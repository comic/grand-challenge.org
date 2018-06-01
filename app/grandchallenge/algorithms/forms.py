# -*- coding: utf-8 -*-
from crispy_forms.helper import FormHelper
from django import forms

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.evaluation.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList

algorithm_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/algorithm-upload/", multifile=False,
)

class AlgorithmForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=algorithm_upload_widget,
        label='Algorithm Image',
        validators=[
            ExtensionValidator(allowed_extensions=('.tar', ))
        ],
        help_text=(
            'Tar archive of the container image produced from the command '
            '`docker save IMAGE > IMAGE.tar`. See '
            'https://docs.docker.com/engine/reference/commandline/save/'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = Algorithm
        fields = ('description', 'chunked_upload',)
