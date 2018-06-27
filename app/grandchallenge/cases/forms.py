# -*- coding: utf-8 -*-
from typing import List

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.http import HttpRequest

from grandchallenge.cases.models import RawImageUploadSession, RawImageFile
from grandchallenge.jqfileupload.models import StagedFile

from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList, \
    StagedAjaxFile


class DuplicateFileRejecter:
    def __init__(self):
        self.request = None

    def install_request_updater(self, func):
        def result(request: HttpRequest, *args, **kwargs):
            self.request = request
            return func(request, *args, **kwargs)
        return result

    def test(self, file: UploadedFile):
        self.request: HttpRequest

        csrf_token = self.request.META.get('CSRF_COOKIE', None)
        client_id = self.request.META.get(
            "X-Upload-ID", self.request.POST.get("X-Upload-ID", None)
        )
        if csrf_token:
            uploaded_files = StagedFile.objects.filter(
                csrf=csrf_token,
                client_filename=file.name,
            )
            if client_id:
                uploaded_files.exclude(client_id=client_id)
            if uploaded_files.exists():
                raise ValidationError("Duplicate file")


duplicate_file_rejecter = DuplicateFileRejecter()
upload_raw_files_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/raw_files/",
    multifile=True,
    auto_commit=False,
    upload_validators=[
        duplicate_file_rejecter.test,
    ],
)


class UploadRawImagesForm(forms.ModelForm):
    files = UploadedAjaxFileList(
        widget=upload_raw_files_widget,
        label="Image files",
        help_text=(
            'Upload images for creating a new archive'
        ),
    )

    def __init__(self, *args, **kwargs):
        super(UploadRawImagesForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("save", "Submit"))

    def save(self, commit=True):
        with transaction.atomic():
            instance = super(UploadRawImagesForm, self).save(commit=commit)

            # Create links between the created session and all uploaded files
            uploaded_files = self.cleaned_data["files"]
            uploaded_files: List[StagedAjaxFile]

            for uploaded_file in uploaded_files:
                RawImageFile.objects.create(
                    upload_session=instance,
                    filename=uploaded_file.name,
                    staged_file_id=uploaded_file.uuid,
                )

        return instance

    class Meta:
        model = RawImageUploadSession
        fields = ['files']

