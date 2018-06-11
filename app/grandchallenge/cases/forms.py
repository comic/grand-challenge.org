# -*- coding: utf-8 -*-
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from grandchallenge.cases.models import Case, RawImageUploadSession
from grandchallenge.evaluation.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList

case_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/case-upload/", multifile=True,
)


class CaseForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=case_upload_widget,
        label='Case Files',
        validators=[
            ExtensionValidator(allowed_extensions=('.mhd', '.raw', '.zraw', ))
        ],
        help_text=(
            'Select the files for this case.'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = Case
        fields = ['chunked_upload']


upload_raw_files_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/raw_files/",
    multifile=True,
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

    class Meta:
        model = RawImageUploadSession
        fields = ['files']

