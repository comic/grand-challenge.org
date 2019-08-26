from crispy_forms.helper import FormHelper
from django import forms

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList

algorithm_image_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/algorithm-image-upload/", multifile=False
)


class AlgorithmImageForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=algorithm_image_upload_widget,
        label="Algorithm Image",
        validators=[
            ExtensionValidator(allowed_extensions=(".tar", ".tar.gz"))
        ],
        help_text=(
            ".tar.gz archive of the container image produced from the command "
            "'docker save IMAGE | gzip -c > IMAGE.tar.gz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = AlgorithmImage
        fields = (
            "title",
            "requires_gpu",
            "description",
            "logo",
            "chunked_upload",
        )
