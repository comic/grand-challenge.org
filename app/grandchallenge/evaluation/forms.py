from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from grandchallenge.evaluation.models import Method, Submission, Config
from grandchallenge.evaluation.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList


class ConfigForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit('save', 'Save'))

    class Meta:
        model = Config
        fields = (
            'use_teams',
            'daily_submission_limit',
            'score_title',
            'score_jsonpath',
            'score_default_sort',
            'extra_results_columns',
            'submission_page_html',
            'new_results_are_public',
            'allow_submission_comments',
            'allow_supplementary_file',
            'require_supplementary_file',
            'supplementary_file_label',
            'supplementary_file_help_text',
            'show_supplementary_file_link',
        )


method_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/method-upload/", multifile=False
)


class MethodForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=method_upload_widget,
        label='Evaluation Method Container',
        validators=[ExtensionValidator(allowed_extensions=('.tar',))],
        help_text=(
            'Tar archive of the container image produced from the command '
            '`docker save IMAGE > IMAGE.tar`. See '
            'https://docs.docker.com/engine/reference/commandline/save/'
        ),
    )

    def __init__(self, *args, **kwargs):
        super(MethodForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = Method
        fields = ['chunked_upload']


submission_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/submission-upload/", multifile=False
)


class SubmissionForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=submission_upload_widget,
        label='Predictions File',
        validators=[ExtensionValidator(allowed_extensions=('.zip', '.csv'))],
    )

    def __init__(self, *args, **kwargs):
        """
        Conditionally render the comment field based on the
        display_comment_field kwarg
        """
        display_comment_field = kwargs.pop('display_comment_field', False)

        allow_supplementary_file = kwargs.pop(
            'allow_supplementary_file', False
        )

        require_supplementary_file = kwargs.pop(
            'require_supplementary_file', False
        )

        supplementary_file_label = kwargs.pop('supplementary_file_label', '')

        supplementary_file_help_text = kwargs.pop(
            'supplementary_file_help_text', ''
        )

        super(SubmissionForm, self).__init__(*args, **kwargs)

        if not display_comment_field:
            del self.fields['comment']

        if supplementary_file_label:
            self.fields['supplementary_file'].label = supplementary_file_label

        if supplementary_file_help_text:
            self.fields[
                'supplementary_file'
            ].help_text = supplementary_file_help_text

        if require_supplementary_file:
            self.fields['supplementary_file'].required = True
        elif not allow_supplementary_file:
            del self.fields['supplementary_file']

        self.helper = FormHelper(self)

    class Meta:
        model = Submission
        fields = ('comment', 'supplementary_file', 'chunked_upload')

class LegacySubmissionForm(SubmissionForm):
    class Meta:
        model = Submission
        fields = (
            'creator',
            'comment',
            'supplementary_file',
            'chunked_upload',
        )
