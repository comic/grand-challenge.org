from bleach import clean
from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Layout, Submit
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models.functions import Lower
from django.forms import CheckboxInput, HiddenInput, ModelChoiceField
from django.utils.html import format_html
from django.utils.text import format_lazy
from django_select2.forms import Select2Widget
from django_summernote.widgets import SummernoteInplaceWidget

from grandchallenge.algorithms.forms import UserAlgorithmsForPhaseMixin
from grandchallenge.components.forms import ContainerImageForm
from grandchallenge.core.forms import (
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.evaluation.models import (
    EXTRA_RESULT_COLUMNS_SCHEMA,
    Evaluation,
    Method,
    Phase,
    Submission,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.hanging_protocols.forms import ViewContentMixin
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget

phase_options = ("title", "public")

submission_options = (
    "submissions_open_at",
    "submissions_close_at",
    "submission_page_html",
    "creator_must_be_verified",
    "submissions_limit_per_user_per_period",
    "submission_limit_period",
    "allow_submission_comments",
    "supplementary_file_choice",
    "supplementary_file_label",
    "supplementary_file_help_text",
    "supplementary_url_choice",
    "supplementary_url_label",
    "supplementary_url_help_text",
)

scoring_options = (
    "score_title",
    "score_jsonpath",
    "score_error_jsonpath",
    "score_default_sort",
    "score_decimal_places",
    "extra_results_columns",
    "scoring_method_choice",
    "auto_publish_new_results",
    "result_display_choice",
)

leaderboard_options = (
    "display_submission_comments",
    "show_supplementary_file_link",
    "show_supplementary_url",
)

result_detail_options = ("display_all_metrics",)

algorithm_setting_options = (
    "workstation",
    "workstation_config",
    "hanging_protocol",
    "view_content",
)


class PhaseTitleMixin:
    def __init__(self, *args, challenge, **kwargs):
        self.challenge = challenge
        super().__init__(*args, **kwargs)

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        qs = self.challenge.phase_set.filter(title__iexact=title)

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError(
                "This challenge already has a phase with this title"
            )

        return title


class PhaseCreateForm(PhaseTitleMixin, SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = Phase
        fields = ("title", "submissions_open_at", "submissions_close_at")
        widgets = {
            "submissions_open_at": forms.DateTimeInput(
                format=("%Y-%m-%dT%H:%M"), attrs={"type": "datetime-local"}
            ),
            "submissions_close_at": forms.DateTimeInput(
                format=("%Y-%m-%dT%H:%M"), attrs={"type": "datetime-local"}
            ),
        }


class PhaseUpdateForm(
    PhaseTitleMixin,
    WorkstationUserFilterMixin,
    ViewContentMixin,
    forms.ModelForm,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            TabHolder(
                Tab("Phase", *phase_options),
                Tab("Submission", *submission_options),
                Tab("Scoring", *scoring_options),
                Tab("Leaderboard", *leaderboard_options),
                Tab("Result Detail", *result_detail_options),
            ),
            ButtonHolder(Submit("save", "Save")),
        )
        if self.instance.submission_kind == SubmissionKindChoices.ALGORITHM:
            self.helper.layout[0].append(
                Tab(
                    "Algorithm",
                    HTML(
                        "<p>Use the settings below to define which "
                        "<a href='https://grand-challenge.org/documentation/viewers/'>viewer</a>, "
                        "<a href='https://grand-challenge.org/documentation/how-to-configure-your-viewer/'>"
                        "viewer configuration</a> and "
                        "<a href='https://grand-challenge.org/documentation/viewer-layout/'>hanging protocol</a> "
                        "the algorithms submitted to this phase should use. Providing these settings is optional "
                        "but recommended. It will ensure that all algorithms are configured in the same way. </p>"
                    ),
                    *algorithm_setting_options,
                )
            )
            self.fields["creator_must_be_verified"].widget = CheckboxInput(
                attrs={"checked": True}
            )

    class Meta:
        model = Phase
        fields = (
            *phase_options,
            *submission_options,
            *scoring_options,
            *leaderboard_options,
            *result_detail_options,
            *algorithm_setting_options,
        )
        widgets = {
            "submission_page_html": SummernoteInplaceWidget(),
            "extra_results_columns": JSONEditorWidget(
                schema=EXTRA_RESULT_COLUMNS_SCHEMA
            ),
            "submissions_open_at": forms.DateTimeInput(
                format=("%Y-%m-%dT%H:%M"), attrs={"type": "datetime-local"}
            ),
            "submissions_close_at": forms.DateTimeInput(
                format=("%Y-%m-%dT%H:%M"), attrs={"type": "datetime-local"}
            ),
        }
        widgets.update(ViewContentMixin.Meta.widgets)
        help_texts = {
            "workstation_config": format_lazy(
                (
                    "The viewer configuration to use for the algorithms submitted to this phase. "
                    "If a suitable configuration does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'configurations, go <a href="{}">here</a>.'
                ),
                reverse_lazy("workstation-configs:create"),
                reverse_lazy("workstation-configs:list"),
            ),
            "hanging_protocol": format_lazy(
                (
                    "The hanging protocol to use for the algorithms submitted to this phase. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
        }
        help_texts.update(ViewContentMixin.Meta.help_texts)
        labels = {
            "workstation": "Viewer",
            "workstation_config": "Viewer Configuration",
        }


class MethodForm(ContainerImageForm):
    phase = ModelChoiceField(
        queryset=None,
        help_text="Which phase is this evaluation container for?",
    )

    def __init__(self, *args, phase, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phase"].queryset = Phase.objects.filter(pk=phase.pk).all()
        self.fields["phase"].initial = phase
        self.fields["phase"].widget = HiddenInput()

    class Meta:
        model = Method
        fields = ("phase", *ContainerImageForm.Meta.fields)


class MethodUpdateForm(SaveFormInitMixin, forms.ModelForm):
    requires_memory_gb = forms.IntegerField(
        min_value=1,
        max_value=16,
        help_text="The maximum system memory required by the algorithm in gigabytes.",
    )

    class Meta:
        model = Method
        fields = (
            "requires_memory_gb",
            "comment",
        )


submission_fields = (
    "creator",
    "phase",
    "comment",
    "supplementary_file",
    "supplementary_url",
    "user_upload",
    "algorithm_image",
)


class SubmissionForm(
    UserAlgorithmsForPhaseMixin, SaveFormInitMixin, forms.ModelForm
):
    user_upload = ModelChoiceField(
        widget=UserUploadSingleWidget(
            allowed_file_types=[
                "application/zip",
                "application/x-zip-compressed",
                "application/csv",
                "application/vnd.ms-excel",
                "text/csv",
                "text/plain",
                "application/json",
            ]
        ),
        label="Predictions File",
        queryset=None,
    )

    def __init__(self, *args, user, phase: Phase, **kwargs):  # noqa: C901
        super().__init__(*args, user=user, phase=phase, **kwargs)
        self.fields["creator"].queryset = get_user_model().objects.filter(
            pk=user.pk
        )
        self.fields["creator"].initial = user

        # Note that the validation of creator and algorithm require
        # access to the phase properties, so those validations
        # would need to be updated if phase selections are allowed.
        self.fields["phase"].queryset = Phase.objects.filter(pk=phase.pk)
        self.fields["phase"].initial = phase

        if not self._phase.allow_submission_comments:
            del self.fields["comment"]

        if self._phase.supplementary_file_label:
            self.fields[
                "supplementary_file"
            ].label = self._phase.supplementary_file_label

        if self._phase.supplementary_file_help_text:
            self.fields["supplementary_file"].help_text = clean(
                self._phase.supplementary_file_help_text
            )

        if self._phase.supplementary_file_choice == Phase.REQUIRED:
            self.fields["supplementary_file"].required = True
        elif self._phase.supplementary_file_choice == Phase.OFF:
            del self.fields["supplementary_file"]

        if self._phase.supplementary_url_label:
            self.fields[
                "supplementary_url"
            ].label = self._phase.supplementary_url_label

        if self._phase.supplementary_url_help_text:
            self.fields["supplementary_url"].help_text = clean(
                self._phase.supplementary_url_help_text
            )

        if self._phase.supplementary_url_choice == Phase.REQUIRED:
            self.fields["supplementary_url"].required = True
        elif self._phase.supplementary_url_choice == Phase.OFF:
            del self.fields["supplementary_url"]

        if self._phase.submission_kind == SubmissionKindChoices.ALGORITHM:
            del self.fields["user_upload"]

            self.fields[
                "algorithm_image"
            ].queryset = self.get_user_active_images_for_phase.order_by(
                "algorithm__title"
            )

            self._algorithm_inputs = self._phase.algorithm_inputs.all()
            self._algorithm_outputs = self._phase.algorithm_outputs.all()
            self.fields["algorithm_image"].help_text = format_lazy(
                "Select one of your algorithms' active images to submit as a solution to this "
                "challenge. The algorithms need to work with the following inputs: {} "
                "and the following outputs: {}. If you have not created your "
                "algorithm yet you can "
                "do so <a href={}>on this page</a>.",
                oxford_comma(self._algorithm_inputs),
                oxford_comma(self._algorithm_outputs),
                reverse(
                    "evaluation:phase-algorithm-create",
                    kwargs={
                        "slug": phase.slug,
                        "challenge_short_name": phase.challenge.short_name,
                    },
                ),
            )
        else:
            del self.fields["algorithm_image"]

            self.fields["user_upload"].queryset = get_objects_for_user(
                user,
                "uploads.change_userupload",
            ).filter(status=UserUpload.StatusChoices.COMPLETED)

    def clean_algorithm_image(self):
        algorithm_image = self.cleaned_data["algorithm_image"]

        if Submission.objects.filter(
            algorithm_image__image_sha256=algorithm_image.image_sha256,
            phase=self._phase,
        ).exists():
            raise ValidationError(
                "A submission for this algorithm container image "
                "for this phase already exists."
            )

        if (
            Evaluation.objects.filter(
                submission__algorithm_image__image_sha256=algorithm_image.image_sha256
            )
            .exclude(
                status__in=[
                    Evaluation.SUCCESS,
                    Evaluation.FAILURE,
                    Evaluation.CANCELLED,
                ]
            )
            .exclude(submission__phase=self._phase)
            .exists()
        ):
            # This causes problems in `set_evaluation_inputs` if two
            # evaluations are running for the same image at the same time
            raise ValidationError(
                "An evaluation for this algorithm is already in progress for "
                "another phase. Please wait for the other evaluation to "
                "complete."
            )

        return algorithm_image

    def clean_creator(self):
        creator = self.cleaned_data["creator"]

        try:
            user_is_verified = creator.verification.is_verified
        except ObjectDoesNotExist:
            user_is_verified = False

        if self._phase.creator_must_be_verified and not user_is_verified:
            error_message = format_html(
                "You must verify your account before you can make a "
                "submission to this phase. Please "
                '<a href="{}"> request verification here</a>.',
                reverse("verifications:create"),
            )

            # Add this to the non-field errors as we use a HiddenInput
            self.add_error(None, error_message)

            raise ValidationError(error_message)

        is_challenge_admin = self._phase.challenge.is_admin(user=creator)
        has_remaining_submissions = (
            self._phase.get_next_submission(user=creator)[
                "remaining_submissions"
            ]
            >= 1
        )
        has_pending_evaluations = self._phase.has_pending_evaluations(
            user=creator
        )

        can_submit = not has_pending_evaluations and (
            has_remaining_submissions or is_challenge_admin
        )

        if not can_submit:
            error_message = "A new submission cannot be created for this user"
            self.add_error(None, error_message)
            raise ValidationError(error_message)

        return creator

    class Meta:
        model = Submission
        fields = submission_fields
        widgets = {"creator": forms.HiddenInput, "phase": forms.HiddenInput}


class LegacySubmissionForm(SubmissionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "creator"
        ].queryset = self._phase.challenge.participants_group.user_set.all().order_by(
            Lower("username")
        )

    def clean(self):
        if Evaluation.objects.filter(
            submission__phase__challenge=self._phase.challenge,
            status=Evaluation.EXECUTING_PREREQUISITES,
        ).exists():
            raise ValidationError(
                "An evaluation for this challenge is still running, please "
                "wait for it to finish."
            )

        return super().clean()

    class Meta(SubmissionForm.Meta):
        widgets = {"creator": Select2Widget, "phase": forms.HiddenInput}
