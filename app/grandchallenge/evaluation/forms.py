from bleach import clean
from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Layout, Submit
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import BooleanField, Case, Exists, OuterRef, When
from django.db.transaction import on_commit
from django.forms import (
    CheckboxInput,
    CheckboxSelectMultiple,
    Form,
    HiddenInput,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
)
from django.utils.html import format_html
from django.utils.text import format_lazy

from grandchallenge.algorithms.forms import UserAlgorithmsForPhaseMixin
from grandchallenge.algorithms.models import Job
from grandchallenge.challenges.models import Challenge, ChallengeRequest
from grandchallenge.components.forms import (
    AdditionalInputsMixin,
    ContainerImageForm,
)
from grandchallenge.components.models import ImportStatusChoices
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.components.tasks import assign_tarball_from_upload
from grandchallenge.core.forms import (
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.core.widgets import (
    JSONEditorWidget,
    MarkdownEditorInlineWidget,
)
from grandchallenge.evaluation.models import (
    EXTRA_RESULT_COLUMNS_SCHEMA,
    CombinedLeaderboard,
    Evaluation,
    EvaluationGroundTruth,
    Method,
    Phase,
    Submission,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.hanging_protocols.forms import ViewContentExampleMixin
from grandchallenge.hanging_protocols.models import VIEW_CONTENT_SCHEMA
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget

phase_options = ("title", "public", "parent")

submission_options = (
    "submissions_open_at",
    "submissions_close_at",
    "submission_page_markdown",
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
    "evaluation_requires_gpu_type",
    "evaluation_requires_memory_gb",
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
    "give_algorithm_editors_job_view_permissions",
    "workstation",
    "workstation_config",
    "hanging_protocol",
    "optional_hanging_protocols",
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
    SaveFormInitMixin,
    ViewContentExampleMixin,
    forms.ModelForm,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["parent"].queryset = self.instance.parent_phase_choices
        self.fields["evaluation_requires_memory_gb"].validators = [
            MinValueValidator(settings.ALGORITHMS_MIN_MEMORY_GB),
            MaxValueValidator(
                self.instance.evaluation_maximum_settable_memory_gb
            ),
        ]
        self.fields["evaluation_requires_gpu_type"].choices = [
            (choice.value, choice.label)
            for choice in GPUTypeChoices
            if choice in self.instance.evaluation_selectable_gpu_type_choices
        ]

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
            "submission_page_markdown": MarkdownEditorInlineWidget,
            "extra_results_columns": JSONEditorWidget(
                schema=EXTRA_RESULT_COLUMNS_SCHEMA
            ),
            "submissions_open_at": forms.DateTimeInput(
                format=("%Y-%m-%dT%H:%M"), attrs={"type": "datetime-local"}
            ),
            "submissions_close_at": forms.DateTimeInput(
                format=("%Y-%m-%dT%H:%M"), attrs={"type": "datetime-local"}
            ),
            "view_content": JSONEditorWidget(schema=VIEW_CONTENT_SCHEMA),
        }
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
            "optional hanging protocols": format_lazy(
                (
                    "Additional, optional hanging protocols to use for the algorithms submitted to this phase. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
        }
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
    class Meta:
        model = Method
        fields = ("comment",)


class AlgorithmChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.form_field_label()


class SubmissionForm(
    UserAlgorithmsForPhaseMixin,
    AdditionalInputsMixin,
    forms.ModelForm,
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
    algorithm = AlgorithmChoiceField(
        queryset=None,
        help_text="Select one of your algorithms to submit as a solution to this phase. See above for information regarding the necessary configuration of the algorithm.",
    )
    confirm_submission = forms.BooleanField(
        required=True,
        label="I understand that by submitting my algorithm image and model "
        "to this phase, I agree to sharing them with the challenge admins. "
        "I also understand that the algorithm image and model will leave "
        "the Grand Challenge platform and that "
        "Grand Challenge will have no control or insight "
        "into their subsequent use, including how frequently, "
        "by who and with what data they will be used.",
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

        if not self._phase.external_evaluation:
            del self.fields["confirm_submission"]

        if not self._phase.allow_submission_comments:
            del self.fields["comment"]

        if self._phase.supplementary_file_label:
            self.fields["supplementary_file"].label = (
                self._phase.supplementary_file_label
            )

        if self._phase.supplementary_file_help_text:
            self.fields["supplementary_file"].help_text = clean(
                self._phase.supplementary_file_help_text
            )

        if self._phase.supplementary_file_choice == Phase.REQUIRED:
            self.fields["supplementary_file"].required = True
        elif self._phase.supplementary_file_choice == Phase.OFF:
            del self.fields["supplementary_file"]

        if self._phase.supplementary_url_label:
            self.fields["supplementary_url"].label = (
                self._phase.supplementary_url_label
            )

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
            qs = self.user_algorithms_for_phase.filter(
                has_active_image=True
            ).order_by("title")
            if self._phase.parent:
                eval_base_query = Evaluation.objects.filter(
                    submission__phase=self._phase.parent,
                    status=Evaluation.SUCCESS,
                    submission__algorithm_image__pk=OuterRef(
                        "active_image_pk"
                    ),
                )
                job_base_query = Job.objects.filter(
                    status=Job.SUCCESS,
                    algorithm_image=OuterRef("active_image_pk"),
                )
                # Query when active_model_pk is not None
                eval_with_active_model = eval_base_query.filter(
                    submission__algorithm_model__pk=OuterRef(
                        "active_model_pk"
                    ),
                )
                job_with_active_model = job_base_query.filter(
                    algorithm_model=OuterRef("active_model_pk"),
                )

                qs = (
                    qs.annotate(
                        has_successful_eval=Case(
                            When(
                                active_model_pk__isnull=False,
                                then=Exists(eval_with_active_model),
                            ),
                            default=Exists(eval_base_query),
                            output_field=BooleanField(),
                        ),
                        has_successful_job=Case(
                            When(
                                active_model_pk__isnull=False,
                                then=Exists(job_with_active_model),
                            ),
                            default=Exists(job_base_query),
                            output_field=BooleanField(),
                        ),
                    )
                    .filter(
                        has_successful_eval=True,
                        has_successful_job=True,
                    )
                    .distinct()
                )

            self.fields["algorithm"].queryset = qs
            self.fields["algorithm_image"].widget = HiddenInput()
            self.fields["algorithm_image"].required = False
            self.fields["algorithm_model"].widget = HiddenInput()

            if (
                not self._phase.active_image
                and not self._phase.external_evaluation
            ):
                self.fields["algorithm"].disabled = True
        else:
            del self.fields["algorithm"]
            del self.fields["algorithm_image"]
            del self.fields["algorithm_model"]

            self.fields["user_upload"].queryset = filter_by_permission(
                queryset=UserUpload.objects.filter(
                    status=UserUpload.StatusChoices.COMPLETED
                ),
                user=user,
                codename="change_userupload",
            )

            if not self._phase.active_image:
                self.fields["user_upload"].disabled = True

        self.init_additional_inputs(
            inputs=self._phase.additional_evaluation_inputs.all()
        )

        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    def clean(self):
        cleaned_data = super().clean()
        if (
            not self._phase.external_evaluation
            and not self._phase.active_image
        ):
            raise ValidationError(
                "You cannot submit to this phase because this phase "
                "does not have an active evaluation method yet."
            )
        if self._phase.external_evaluation and not self.cleaned_data.get(
            "confirm_submission", None
        ):
            raise ValidationError(
                "You must confirm that you want to submit to this phase."
            )

        cleaned_data["additional_inputs"] = self.clean_additional_inputs()

        return cleaned_data

    def clean_phase(self):
        phase = self.cleaned_data["phase"]
        if (
            phase.submission_kind == SubmissionKindChoices.ALGORITHM
            and not phase.external_evaluation
            and phase.jobs_to_schedule_per_submission == 0
        ):
            self.add_error(
                None,
                "This phase is not ready for submissions yet. There are no valid archive items in the archive linked to this phase.",
            )
        return phase

    def clean_algorithm(self):
        algorithm = self.cleaned_data["algorithm"]

        if algorithm.active_model:
            extra_submission_filter = {
                "algorithm_model__sha256": algorithm.active_model.sha256
            }
        else:
            extra_submission_filter = {"algorithm_model__isnull": True}

        if Submission.objects.filter(
            algorithm_image__image_sha256=algorithm.active_image.image_sha256,
            phase=self._phase,
            **extra_submission_filter,
        ).exists():
            raise ValidationError(
                "A submission for this algorithm container image and model "
                "for this phase already exists."
            )

        if (
            Evaluation.objects.active()
            .filter(
                submission__algorithm_image__image_sha256=algorithm.active_image.image_sha256,
            )
            .exists()
        ):
            # This causes problems in `set_evaluation_inputs` if two
            # evaluations are running for the same image at the same time
            raise ValidationError(
                "An evaluation for this algorithm is already in progress for "
                "another phase. Please wait for the other evaluation to "
                "complete."
            )

        job_requirement_errors = []
        phase = self.cleaned_data["phase"]
        if (
            algorithm.job_requires_memory_gb
            > phase.algorithm_maximum_settable_memory_gb
        ):
            job_requirement_errors.append(
                ValidationError(
                    "The requested memory for this algorithm "
                    f"({algorithm.job_requires_memory_gb}) is too high for this "
                    "phase. The maximum allowed memory is "
                    f"{phase.algorithm_maximum_settable_memory_gb} GB. "
                    "Please adjust the setting on the algorithm."
                )
            )
        if (
            algorithm.job_requires_gpu_type
            not in phase.algorithm_selectable_gpu_type_choices
        ):
            job_requirement_errors.append(
                ValidationError(
                    "The requested GPU type for this algorithm "
                    f"({GPUTypeChoices(algorithm.job_requires_gpu_type).name}) is "
                    "not allowed for this phase. Options are: "
                    f"{', '.join([GPUTypeChoices(c).name for c in phase.algorithm_selectable_gpu_type_choices])}. "
                    "Please adjust the setting on the algorithm."
                )
            )
        if job_requirement_errors:
            raise ValidationError(job_requirement_errors)

        self.cleaned_data["algorithm_image"] = algorithm.active_image
        self.cleaned_data["algorithm_model"] = algorithm.active_model

        return algorithm

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

        has_available_compute = (
            self._phase.challenge.available_compute_euro_millicents > 0
        )
        is_challenge_admin = self._phase.challenge.is_admin(user=creator)
        has_remaining_submissions = (
            self._phase.get_next_submission(user=creator)[
                "remaining_submissions"
            ]
            >= 1
        )
        has_pending_evaluations = self._phase.has_pending_evaluations(
            user_pks=[creator.pk]
        )

        can_submit = (
            has_available_compute
            and not has_pending_evaluations
            and (has_remaining_submissions or is_challenge_admin)
        )

        if not can_submit:
            self.raise_submission_limit_error()
        elif has_available_compute and not is_challenge_admin:
            self.check_submission_limit_avoidance(creator=creator)

        return creator

    def raise_submission_limit_error(self):
        error_message = "You cannot create a new submission at this time"
        self.add_error(None, error_message)
        raise ValidationError(error_message)

    def _get_submission_relevant_users(self, *, creator):
        return (
            get_user_model()
            .objects.exclude(pk=creator.pk)
            .exclude(groups__admins_of_challenge__phase=self._phase)
            .filter(
                verificationuserset__users=creator,
                verificationuserset__is_false_positive=False,
            )
            .distinct()
        )

    def check_submission_limit_avoidance(self, *, creator):
        related_users = self._get_submission_relevant_users(creator=creator)

        if related_users and (
            self._phase.has_pending_evaluations(
                user_pks=[related_user.pk for related_user in related_users]
            )
            or any(
                self._phase.get_next_submission(user=related_user)[
                    "remaining_submissions"
                ]
                < 1
                for related_user in related_users
            )
        ):
            self._phase.handle_submission_limit_avoidance(user=creator)
            self.raise_submission_limit_error()

    def save(self, *args, **kwargs):
        if self._phase.submission_kind == SubmissionKindChoices.ALGORITHM:
            self.instance.algorithm_requires_gpu_type = self.cleaned_data[
                "algorithm_image"
            ].algorithm.job_requires_gpu_type
            self.instance.algorithm_requires_memory_gb = self.cleaned_data[
                "algorithm_image"
            ].algorithm.job_requires_memory_gb
        else:
            self.instance.algorithm_requires_gpu_type = GPUTypeChoices.NO_GPU
            self.instance.algorithm_requires_memory_gb = 0

        instance = super().save(*args, **kwargs)

        instance.create_evaluation(
            additional_inputs=self.cleaned_data["additional_inputs"]
        )

        return instance

    class Meta:
        model = Submission
        fields = (
            "creator",
            "phase",
            "comment",
            "supplementary_file",
            "supplementary_url",
            "user_upload",
            "algorithm_image",
            "algorithm_model",
        )
        widgets = {"creator": forms.HiddenInput, "phase": forms.HiddenInput}


class CombinedLeaderboardForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, challenge, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["phases"].queryset = challenge.phase_set.all()

    class Meta:
        model = CombinedLeaderboard
        fields = ("title", "description", "phases", "combination_method")
        widgets = {"phases": forms.CheckboxSelectMultiple}


class EvaluationForm(AdditionalInputsMixin, forms.Form):
    submission = ModelChoiceField(
        queryset=None, disabled=True, widget=HiddenInput()
    )

    def __init__(self, submission, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._user = user

        self.fields["submission"].queryset = filter_by_permission(
            queryset=Submission.objects.filter(pk=submission.pk),
            user=user,
            codename="view_submission",
        )
        self.fields["submission"].initial = submission

        self.init_additional_inputs(
            inputs=submission.phase.additional_evaluation_inputs.all()
        )

        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    def clean(self):
        cleaned_data = super().clean()

        if (
            cleaned_data["submission"].phase.submission_kind
            == SubmissionKindChoices.ALGORITHM
        ):
            if not cleaned_data[
                "submission"
            ].has_matching_algorithm_interfaces:
                raise ValidationError(
                    "The algorithm interfaces do not match those "
                    "defined for the phase."
                )

        if (
            Evaluation.objects.active()
            .filter(
                submission__algorithm_image__image_sha256=cleaned_data[
                    "submission"
                ].algorithm_image.image_sha256,
            )
            .exists()
        ):
            # This causes problems in `set_evaluation_inputs` if two
            # evaluations are running for the same image at the same time
            raise ValidationError(
                "An evaluation for this algorithm is already in progress. "
                "Please wait for the other evaluation to complete."
            )

        # Fetch from the db to get the cost annotations
        # Maybe this is solved with GeneratedField (Django 5)?
        challenge = (
            Challenge.objects.filter(
                pk=cleaned_data["submission"].phase.challenge.pk
            )
            .with_available_compute()
            .get()
        )

        if challenge.available_compute_euro_millicents <= 0:
            raise ValidationError("This challenge has exceeded its budget")

        cleaned_data["additional_inputs"] = self.clean_additional_inputs()

        if Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=cleaned_data["additional_inputs"],
            submission=cleaned_data["submission"],
            method=cleaned_data["submission"].phase.active_image,
            ground_truth=cleaned_data["submission"].phase.active_ground_truth,
            time_limit=cleaned_data["submission"].phase.evaluation_time_limit,
            requires_gpu_type=cleaned_data[
                "submission"
            ].phase.evaluation_requires_gpu_type,
            requires_memory_gb=cleaned_data[
                "submission"
            ].phase.evaluation_requires_memory_gb,
        ):
            raise ValidationError(
                "A result for these inputs with the current method "
                "and ground truth already exists."
            )

        return cleaned_data


class ConfigureAlgorithmPhasesForm(SaveFormInitMixin, Form):
    phases = ModelMultipleChoiceField(
        queryset=None,
        widget=CheckboxSelectMultiple,
    )
    algorithm_time_limit = IntegerField(
        widget=forms.HiddenInput(),
        disabled=True,
    )
    algorithm_selectable_gpu_type_choices = forms.JSONField(
        widget=forms.HiddenInput(),
        disabled=True,
    )
    algorithm_maximum_settable_memory_gb = forms.IntegerField(
        widget=forms.HiddenInput(),
        disabled=True,
    )

    def __init__(self, *args, challenge, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phases"].queryset = (
            Phase.objects.select_related("challenge")
            .filter(
                challenge=challenge,
                submission_kind=SubmissionKindChoices.CSV,
                submission__isnull=True,
                method__isnull=True,
            )
            .all()
        )

        try:
            challenge_request = ChallengeRequest.objects.get(
                short_name=challenge.short_name
            )
        except ObjectDoesNotExist:
            challenge_request = None
        if challenge_request:
            self.fields["algorithm_selectable_gpu_type_choices"].initial = (
                challenge_request.algorithm_selectable_gpu_type_choices
            )
            self.fields["algorithm_maximum_settable_memory_gb"].initial = (
                challenge_request.algorithm_maximum_settable_memory_gb
            )
            self.fields["algorithm_time_limit"].initial = (
                challenge_request.inference_time_limit_in_minutes * 60
            )
        else:
            self.fields["algorithm_selectable_gpu_type_choices"].initial = (
                Phase._meta.get_field(
                    "algorithm_selectable_gpu_type_choices"
                ).get_default()
            )
            self.fields["algorithm_maximum_settable_memory_gb"].initial = (
                Phase._meta.get_field(
                    "algorithm_maximum_settable_memory_gb"
                ).get_default()
            )
            self.fields["algorithm_time_limit"].initial = (
                Phase._meta.get_field("algorithm_time_limit").get_default()
            )


class EvaluationGroundTruthForm(SaveFormInitMixin, ModelForm):
    phase = ModelChoiceField(widget=HiddenInput(), queryset=None)
    user_upload = ModelChoiceField(
        widget=UserUploadSingleWidget(
            allowed_file_types=[
                "application/x-gzip",
                "application/gzip",
            ]
        ),
        label="Ground Truth",
        queryset=None,
        help_text=(
            ".tar.gz file of the ground truth that will be extracted"
            " to /opt/ml/input/data/ground_truth/ during evaluation"
        ),
    )
    creator = ModelChoiceField(
        widget=HiddenInput(),
        queryset=(
            get_user_model()
            .objects.exclude(username=settings.ANONYMOUS_USER_NAME)
            .filter(verification__is_verified=True)
        ),
    )

    def __init__(self, *args, user, phase, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user_upload"].queryset = filter_by_permission(
            queryset=UserUpload.objects.filter(
                status=UserUpload.StatusChoices.COMPLETED
            ),
            user=user,
            codename="change_userupload",
        )

        self.fields["creator"].initial = user
        self.fields["phase"].queryset = Phase.objects.filter(pk=phase.pk)
        self.fields["phase"].initial = phase

    def clean_creator(self):
        creator = self.cleaned_data["creator"]

        if EvaluationGroundTruth.objects.filter(
            import_status=ImportStatusChoices.INITIALIZED,
            creator=creator,
        ).exists():
            self.add_error(
                None,
                "You have an existing ground truth importing, please wait for it to complete",
            )

        return creator

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        on_commit(
            assign_tarball_from_upload.signature(
                kwargs={
                    "app_label": instance._meta.app_label,
                    "model_name": instance._meta.model_name,
                    "tarball_pk": instance.pk,
                    "field_to_copy": "ground_truth",
                },
                immutable=True,
            ).apply_async
        )
        return instance

    class Meta:
        model = EvaluationGroundTruth
        fields = ("phase", "user_upload", "creator", "comment")


class EvaluationGroundTruthUpdateForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = EvaluationGroundTruth
        fields = ("comment",)


class EvaluationGroundTruthVersionManagementForm(Form):
    ground_truth = ModelChoiceField(
        queryset=EvaluationGroundTruth.objects.none()
    )

    def __init__(
        self,
        *args,
        user,
        phase,
        activate,
        hide_ground_truth_input=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._activate = activate

        extra_filter = {}
        if self._activate:
            extra_filter["import_status"] = ImportStatusChoices.COMPLETED

        self.fields["ground_truth"].queryset = filter_by_permission(
            queryset=EvaluationGroundTruth.objects.filter(
                phase=phase,
                is_desired_version=False if activate else True,
                **extra_filter,
            ).select_related("phase"),
            user=user,
            codename="change_evaluationgroundtruth",
        )

        if hide_ground_truth_input:
            self.fields["ground_truth"].widget = HiddenInput()

        self.helper = FormHelper(self)
        if activate:
            self.helper.layout.append(Submit("save", "Activate ground truth"))
            self.helper.form_action = reverse(
                "evaluation:ground-truth-activate",
                kwargs={
                    "slug": phase.slug,
                    "challenge_short_name": phase.challenge.short_name,
                },
            )
        else:
            self.helper.layout.append(
                Submit("save", "Deactivate ground truth")
            )
            self.helper.form_action = reverse(
                "evaluation:ground-truth-deactivate",
                kwargs={
                    "slug": phase.slug,
                    "challenge_short_name": phase.challenge.short_name,
                },
            )

    def clean_ground_truth(self):
        ground_truth = self.cleaned_data["ground_truth"]

        if ground_truth.phase.ground_truth_upload_in_progress:
            raise ValidationError("Ground truth updating already in progress.")

        return ground_truth


class AlgorithmInterfaceForPhaseCopyForm(Form):
    phases = ModelMultipleChoiceField(
        queryset=Phase.objects.none(),
        label="Select the phases to copy the interfaces to",
        widget=CheckboxSelectMultiple,
    )

    def __init__(self, *args, phase, **kwargs):
        super().__init__(*args, **kwargs)
        self._phase = phase

        self.fields["phases"].queryset = Phase.objects.filter(
            challenge=phase.challenge,
            submission_kind=phase.submission_kind,
        ).exclude(pk=phase.pk)

    def clean_phases(self):
        phases = self.cleaned_data["phases"]

        locked_phases = [
            phase for phase in phases if phase.algorithm_interfaces_locked
        ]
        if locked_phases:
            locked_phase_titles = ", ".join(
                phase.title for phase in locked_phases
            )
            raise ValidationError(
                f"You cannot copy algorithm interfaces to the following locked phases: {locked_phase_titles}."
            )

        return phases

    def copy_algorithm_interfaces(self):
        for phase in self.cleaned_data["phases"]:
            for interface in self._phase.algorithm_interfaces.all():
                phase.algorithm_interface_manager.add(interface)
