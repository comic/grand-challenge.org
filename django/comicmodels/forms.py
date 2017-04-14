from django import forms
from comicmodels.models import UploadModel

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
        exclude = ['title','comicsite','permission_lvl','user']
