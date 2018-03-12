from django import forms

from comicmodels.models import UploadModel


class UserUploadForm(forms.ModelForm):
    """ For uploading a file to a specific comicsite. You cannot choose
    to which comicsite to upload
    """

    class Meta:
        model = UploadModel
        exclude = ['title', 'comicsite', 'permission_lvl', 'user']


class CKUploadForm(forms.ModelForm):
    upload = forms.FileField()

    class Meta:
        model = UploadModel
        fields = ('upload',)
