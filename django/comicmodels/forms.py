from django import forms
from comicmodels.models import UploadModel

class UploadForm(forms.ModelForm):
    
    class Meta:
        model = UploadModel
