from django import forms

from grandchallenge.uploads.models import UploadModel


class UserUploadForm(forms.ModelForm):
    """ For uploading a file to a specific challenge. You cannot choose
    to which challenge to upload
    """

    class Meta:
        model = UploadModel
        fields = ('file',)


class CKUploadForm(forms.ModelForm):
    """ This form is used from CKEditor as the file field is named upload """
    upload = forms.ImageField()

    class Meta:
        model = UploadModel
        fields = ('upload',)
