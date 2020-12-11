from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Layout, Submit
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models.functions import Lower
from django.forms import ModelChoiceField
from django.utils.html import format_html
from django.utils.text import format_lazy
from django_select2.forms import Select2Widget
from django_summernote.widgets import SummernoteInplaceWidget
from guardian.shortcuts import get_objects_for_user

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.evaluation.models import (
    EXTRA_RESULT_COLUMNS_SCHEMA,
    Method,
    Phase,
    Submission,
)
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList
from grandchallenge.subdomains.utils import reverse, reverse_lazy

phase_options = ("title",)

submission_options = (
    "submission_page_html",
    "creator_must_be_verified",
    "daily_submission_limit",
    "allow_submission_comments",
    "supplementary_file_choice",
    "supplementary_file_label",
    "supplementary_file_help_text",
    "publication_url_choice",
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
    "show_publication_url",
    "evaluation_comparison_observable_url",
)

result_detail_options = (
    "display_all_metrics",
    "evaluation_detail_observable_url",
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
        fields = ("title",)


class PhaseUpdateForm(PhaseTitleMixin, forms.ModelForm):
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

    class Meta:
        model = Phase
        fields = (
            *phase_options,
            *submission_options,
            *scoring_options,
            *leaderboard_options,
            *result_detail_options,
        )
        widgets = {
            "submission_page_html": SummernoteInplaceWidget(),
            "extra_results_columns": JSONEditorWidget(
                schema=EXTRA_RESULT_COLUMNS_SCHEMA
            ),
        }


class MethodForm(SaveFormInitMixin, forms.ModelForm):
    phase = ModelChoiceField(
        queryset=None,
        help_text="Which phase is this evaluation container for?",
    )
    chunked_upload = UploadedAjaxFileList(
        widget=uploader.AjaxUploadWidget(multifile=False, auto_commit=False),
        label="Evaluation Method Container",
        validators=[
            ExtensionValidator(allowed_extensions=(".tar", ".tar.gz"))
        ],
        help_text=(
            ".tar.gz archive of the container image produced from the command "
            "'docker save IMAGE | gzip -c > IMAGE.tar.gz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
    )

    def __init__(self, *args, user, challenge, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chunked_upload"].widget.user = user
        self.fields["phase"].queryset = challenge.phase_set.all()

    class Meta:
        model = Method
        fields = ["phase", "chunked_upload"]


submission_fields = (
    "creator",
    "comment",
    "supplementary_file",
    "publication_url",
    "chunked_upload",
)


class SubmissionForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=uploader.AjaxUploadWidget(multifile=False, auto_commit=False),
        label="Predictions File",
        validators=[ExtensionValidator(allowed_extensions=(".zip", ".csv"))],
    )
    algorithm = ModelChoiceField(
        queryset=None,
        help_text=format_lazy(
            "Select one of your algorithms to submit as a solution to this "
            "challenge. If you have not created your algorithm yet you can "
            "do so <a href={}>on this page</a>.",
            reverse_lazy("algorithms:create"),
        ),
    )

    def __init__(
        self,
        *args,
        user,
        creator_must_be_verified=False,
        algorithm_submission=False,
        display_comment_field=False,
        supplementary_file_choice=Phase.OFF,
        supplementary_file_label="",
        supplementary_file_help_text="",
        publication_url_choice=Phase.OFF,
        **kwargs,
    ):
        """
        Conditionally render the comment field based on the
        display_comment_field kwarg
        """
        super().__init__(*args, **kwargs)

        self.creator_must_be_verified = creator_must_be_verified

        if not display_comment_field:
            del self.fields["comment"]

        if supplementary_file_label:
            self.fields["supplementary_file"].label = supplementary_file_label

        if supplementary_file_help_text:
            self.fields[
                "supplementary_file"
            ].help_text = supplementary_file_help_text

        if supplementary_file_choice == Phase.REQUIRED:
            self.fields["supplementary_file"].required = True
        elif supplementary_file_choice == Phase.OFF:
            del self.fields["supplementary_file"]

        if publication_url_choice == Phase.REQUIRED:
            self.fields["publication_url"].required = True
        elif publication_url_choice == Phase.OFF:
            del self.fields["publication_url"]

        if algorithm_submission:
            del self.fields["chunked_upload"]

            self.fields["algorithm"].queryset = get_objects_for_user(
                user,
                f"{Algorithm._meta.app_label}.change_{Algorithm._meta.model_name}",
                Algorithm,
            ).order_by("title")
        else:
            del self.fields["algorithm"]

            self.fields["chunked_upload"].widget.user = user

        self.fields["creator"].queryset = get_user_model().objects.filter(
            pk=user.pk
        )
        self.fields["creator"].initial = user

        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    def clean_algorithm(self):
        algorithm = self.cleaned_data["algorithm"]

        if algorithm.latest_ready_image is None:
            raise ValidationError(
                "This algorithm does not have a usable container image. "
                "Please add one and try again."
            )

        return algorithm

    def clean_creator(self):
        creator = self.cleaned_data["creator"]

        try:
            user_is_verified = creator.verification.is_verified
        except ObjectDoesNotExist:
            user_is_verified = False

        if self.creator_must_be_verified and not user_is_verified:
            error_message = format_html(
                "You must verify your account before you can make a "
                "submission to this phase. Please "
                '<a href="{}"> request verification here</a>.',
                reverse("verifications:create"),
            )

            # Add this to the non-field errors as we use a HiddenInput
            self.add_error(None, error_message)

            raise ValidationError(error_message)

        return creator

    class Meta:
        model = Submission
        fields = submission_fields
        widgets = {"creator": forms.HiddenInput}


class LegacySubmissionForm(SubmissionForm):
    def __init__(self, *args, challenge, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "creator"
        ].queryset = challenge.participants_group.user_set.all().order_by(
            Lower("username")
        )

        # For legacy submissions an admin is able to create submissions
        # for any participant
        self.creator_must_be_verified = False

    class Meta(SubmissionForm.Meta):
        widgets = {"creator": Select2Widget}
