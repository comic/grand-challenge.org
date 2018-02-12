from crispy_forms.helper import FormHelper
from django import forms

from evaluation.models import Method, Submission
from evaluation.validators import ExtensionValidator
from jqfileupload.widgets import uploader
from jqfileupload.widgets.uploader import UploadedAjaxFileList

method_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/method-upload/",
    multifile=False)


class MethodForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=method_upload_widget,
        label='Evaluation Method Container',
        validators=[
            ExtensionValidator(
                allowed_extensions=(
                    '.tar',
                )
            ),
        ],
        help_text='Tar archive of the container '
                  'image produced from the command '
                  '`docker save IMAGE > '
                  'IMAGE.tar`. See '
                  'https://docs.docker.com/engine/reference/commandline/save/',
    )

    def __init__(self, *args, **kwargs):
        super(MethodForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = Method
        fields = ['chunked_upload']

class SubmissionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        """
        Conditionally render the comment field based on the
        display_comment_field kwarg
        """

        display_comment_field = kwargs.get('display_comment_field', False)
        if 'display_comment_field' in kwargs:
            del kwargs['display_comment_field']

        super(SubmissionForm, self).__init__(*args, **kwargs)

        if not display_comment_field:
            del self.fields['comment']

        self.helper = FormHelper(self)

    class Meta:
        model = Submission
        fields = (
            'file',
            'comment',
        )
        labels = {
            'file': 'Predictions File',
        }

