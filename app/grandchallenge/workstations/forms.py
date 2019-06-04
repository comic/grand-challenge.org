from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ModelForm

from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.workstations.models import Workstation, WorkstationImage


class WorkstationForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = Workstation
        fields = ("title", "logo", "description")


workstation_image_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/workstation-image-upload/", multifile=False
)


class WorkstationImageForm(ModelForm):
    chunked_upload = uploader.UploadedAjaxFileList(
        widget=workstation_image_upload_widget,
        label="Workstation Image",
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
        model = WorkstationImage
        fields = (
            "initial_path",
            "http_port",
            "websocket_port",
            "chunked_upload",
        )
