from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.core.validators import (
    ExtensionValidator,
    MimeTypeValidator,
)
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList

algorithm_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/algorithm-upload/", multifile=False
)


class AlgorithmForm(forms.ModelForm):
    ipython_notebook = forms.FileField(
        validators=[MimeTypeValidator(allowed_types=("text/plain",))],
        required=False,
        help_text=(
            "Please upload an iPython notebook that describes your algorithm"
        ),
    )
    chunked_upload = UploadedAjaxFileList(
        widget=algorithm_upload_widget,
        label="Algorithm Image",
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
        model = Algorithm
        fields = (
            "title",
            "requires_gpu",
            "ipython_notebook",
            "chunked_upload",
        )
