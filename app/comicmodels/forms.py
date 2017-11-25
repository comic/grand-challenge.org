from crispy_forms.layout import Submit
from django import forms

from comicmodels.models import UploadModel, ComicSite
from crispy_forms.helper import FormHelper


class UploadForm(forms.ModelForm):
    class Meta:
        model = UploadModel
        fields = '__all__'


class UserUploadForm(forms.ModelForm):
    """ For uploading a file to a specific comicsite. You cannot choose
    to which comicsite to upload
    """

    class Meta:
        model = UploadModel
        exclude = ['title', 'comicsite', 'permission_lvl', 'user']


class ChallengeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ChallengeForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit('save', 'save'))

    class Meta:
        model = ComicSite
        exclude = ('creator',)
