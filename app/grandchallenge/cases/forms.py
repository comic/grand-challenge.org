from typing import List

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from grandchallenge.cases.models import RawImageFile, RawImageUploadSession
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import (
    StagedAjaxFile,
    UploadedAjaxFileList,
)


class UploadRawImagesForm(forms.ModelForm):
    files = UploadedAjaxFileList(
        widget=uploader.AjaxUploadWidget(multifile=True, auto_commit=False),
        label="Image files",
        help_text=(
            "The total size of all uploaded files cannot exceed 10 GB.<br>"
            "The following file formats are supported: "
            ".mha, .mhd, .raw, .zraw, .tiff."
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("save", "Submit"))
        self.fields["files"].widget.user = user

    def clean_files(self):
        files = self.cleaned_data["files"]

        if len({f.name for f in files}) != len(files):
            raise ValidationError("Filenames must be unique.")

        if sum([f.size for f in files]) > 15_000_000_000:
            raise ValidationError(
                "Total size of all files exceeds the upload limit."
            )

        return files

    def save(self, commit=True):
        instance = super().save(commit=False)  # type: RawImageUploadSession

        # Create links between the created session and all uploaded files
        uploaded_files = self.cleaned_data[
            "files"
        ]  # type: List[StagedAjaxFile]

        raw_files = [
            RawImageFile(
                upload_session=instance,
                filename=uploaded_file.name,
                staged_file_id=uploaded_file.uuid,
            )
            for uploaded_file in uploaded_files
        ]

        if commit:
            instance.save()
            RawImageFile.objects.bulk_create(raw_files)
            instance.process_images()

        return instance

    class Meta:
        model = RawImageUploadSession
        fields = ["files"]
