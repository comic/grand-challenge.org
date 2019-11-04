from django import forms

from grandchallenge.uploads.models import UploadModel


class UserUploadForm(forms.ModelForm):
    """For uploading a file to a specific challenge."""

    class Meta:
        model = UploadModel
        fields = ("file",)
