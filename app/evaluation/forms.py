from django import forms

from evaluation.widgets import uploader


test_upload_widget = uploader.AjaxUploadWidget(ajax_target_path="/ajax_upload")

class UploadForm(forms.Form):
    title = forms.CharField(label="Blah")
    something = forms.CharField(label="Blabl")
    upload_form = forms.CharField(widget=test_upload_widget)
