from typing import List

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from grandchallenge.cases.models import RawImageUploadSession, RawImageFile
from grandchallenge.jqfileupload.filters import reject_duplicate_filenames
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import (
    UploadedAjaxFileList,
    StagedAjaxFile,
)

upload_raw_files_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/raw_files/",
    multifile=True,
    auto_commit=False,
    upload_validators=[reject_duplicate_filenames],
)


class UploadRawImagesForm(forms.ModelForm):
    files = UploadedAjaxFileList(
        widget=upload_raw_files_widget,
        label="Image files",
        help_text=("Upload images for creating a new archive"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("save", "Submit"))

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
            instance.save(skip_processing=True)
            RawImageFile.objects.bulk_create(raw_files)
            instance.process_images()

        return instance

    class Meta:
        model = RawImageUploadSession
        fields = ["files"]
