from django import forms

from comicmodels.models import UploadModel


class UserUploadForm(forms.ModelForm):
    """ For uploading a file to a specific comicsite. You cannot choose
    to which comicsite to upload
    """

    class Meta:
        model = UploadModel
        fields = ('file',)


class CKUploadForm(forms.ModelForm):
    """ This form is used from CKEditor as the file field is named upload """
    upload = forms.FileField()

    class Meta:
        model = UploadModel
        fields = ('upload',)
