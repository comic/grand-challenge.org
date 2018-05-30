# -*- coding: utf-8 -*-
from crispy_forms.helper import FormHelper
from django import forms

from grandchallenge.cases.models import Case
from grandchallenge.evaluation.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList

case_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/case-upload/", multifile=False
)


class CaseForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=case_upload_widget,
        label='The case',
        validators=[ExtensionValidator(allowed_extensions=('.mha',))],
        help_text=(
            'Select the .mha file that you want to use.'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = Case
        fields = ['chunked_upload']
