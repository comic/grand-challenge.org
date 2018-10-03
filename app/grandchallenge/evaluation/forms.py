from crispy_forms.bootstrap import TabHolder, Tab
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, ButtonHolder
from django import forms

from grandchallenge.evaluation.models import Method, Submission, Config
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList

submission_options = (
    "submission_page_html",
    "daily_submission_limit",
    "allow_submission_comments",
    "supplementary_file_choice",
    "supplementary_file_label",
    "supplementary_file_help_text",
    "publication_url_choice",
)

result_list_options = (
    "use_teams",
    "score_title",
    "score_jsonpath",
    "score_default_sort",
    "score_decimal_places",
    "extra_results_columns",
    "new_results_are_public",
    "display_submission_comments",
    "show_supplementary_file_link",
    "show_publication_url",
)

result_detail_options = ("submission_join_key",)


class ConfigForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            TabHolder(
                Tab("Submission", *submission_options),
                Tab("Result List", *result_list_options),
                Tab("Result Detail", *result_detail_options),
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    class Meta:
        model = Config
        fields = (
            *submission_options,
            *result_list_options,
            *result_detail_options,
        )


method_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/method-upload/", multifile=False
)


class MethodForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=method_upload_widget,
        label="Evaluation Method Container",
        validators=[ExtensionValidator(allowed_extensions=(".tar",))],
        help_text=(
            "Tar archive of the container image produced from the command "
            "`docker save IMAGE > IMAGE.tar`. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = Method
        fields = ["chunked_upload"]


submission_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/submission-upload/", multifile=False
)


class SubmissionForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=submission_upload_widget,
        label="Predictions File",
        validators=[ExtensionValidator(allowed_extensions=(".zip", ".csv"))],
    )

    def __init__(self, *args, **kwargs):
        """
        Conditionally render the comment field based on the
        display_comment_field kwarg
        """
        display_comment_field = kwargs.pop("display_comment_field", False)

        supplementary_file_choice = kwargs.pop(
            "supplementary_file_choice", Config.OFF
        )

        supplementary_file_label = kwargs.pop("supplementary_file_label", "")

        supplementary_file_help_text = kwargs.pop(
            "supplementary_file_help_text", ""
        )

        publication_url_choice = kwargs.pop(
            "publication_url_choice", Config.OFF
        )

        super().__init__(*args, **kwargs)

        if not display_comment_field:
            del self.fields["comment"]

        if supplementary_file_label:
            self.fields["supplementary_file"].label = supplementary_file_label

        if supplementary_file_help_text:
            self.fields[
                "supplementary_file"
            ].help_text = supplementary_file_help_text

        if supplementary_file_choice == Config.REQUIRED:
            self.fields["supplementary_file"].required = True
        elif supplementary_file_choice == Config.OFF:
            del self.fields["supplementary_file"]

        if publication_url_choice == Config.REQUIRED:
            self.fields["publication_url"].required = True
        elif publication_url_choice == Config.OFF:
            del self.fields["publication_url"]

        self.helper = FormHelper(self)

    class Meta:
        model = Submission
        fields = (
            "comment",
            "supplementary_file",
            "publication_url",
            "chunked_upload",
        )


class LegacySubmissionForm(SubmissionForm):
    class Meta:
        model = Submission
        fields = ("creator", "comment", "supplementary_file", "chunked_upload")
