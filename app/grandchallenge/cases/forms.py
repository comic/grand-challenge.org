from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelMultipleChoiceField

from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadMultipleWidget

IMAGE_UPLOAD_HELP_TEXT = """
The total size of all files uploaded in a single session cannot exceed 10 GB.
A maximum of 100 files can be uploaded per session. Please only upload one volume per session.
<br>
If your volume is made up of multiple individual slices (e.g. DICOM files), please
compress the entire directory into a single .zip file and upload that file.
<br>
The following file formats are supported and will be converted to MHA format:
.mha, .mhd, .raw, .zraw, .dcm, .nii, .nii.gz, .nrrd, .fda, .fds, .png, .jpeg, and .jpg.
<br>
The following file formats can be uploaded and will be converted to TIF format:
.tiff, Aperio (.svs), Hamamatsu (.vms, .vmu, .ndpi), Leica (.scn), MIRAX (.mrxs),
Ventana (.bif), and DICOM-WSI (.dcm).
"""


class UploadRawImagesForm(SaveFormInitMixin, forms.ModelForm):
    user_uploads = ModelMultipleChoiceField(
        widget=UserUploadMultipleWidget,
        label="Image files",
        help_text=IMAGE_UPLOAD_HELP_TEXT,
        queryset=None,
    )

    def __init__(self, *args, user, linked_task=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user_uploads"].queryset = filter_by_permission(
            queryset=UserUpload.objects.filter(
                status=UserUpload.StatusChoices.COMPLETED
            ),
            user=user,
            codename="change_userupload",
        )

        self._linked_task = linked_task

    def clean_user_uploads(self):
        user_uploads = self.cleaned_data["user_uploads"]

        if len({f.filename for f in user_uploads}) != len(user_uploads):
            raise ValidationError("Filenames must be unique.")

        return user_uploads

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.process_images(linked_task=self._linked_task)
        return instance

    class Meta:
        model = RawImageUploadSession
        fields = ("user_uploads",)
