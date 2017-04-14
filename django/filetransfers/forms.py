from django import forms
from filetransfers.models import UploadModel

class UploadForm(forms.ModelForm):
    class Meta:
        model = UploadModel
        fields = '__all__'
