from django import forms

from evaluation.widgets import uploader


test_upload_widget = uploader.AjaxUploadWidget(ajax_target_path="ajax/ulwidget1")
test_upload_widget2 = uploader.AjaxUploadWidget(ajax_target_path="ajax/ulwidget2")

class UploadForm(forms.Form):
    title = forms.CharField(label="Blah")
    something = forms.CharField(label="Blabl")
    upload_form = forms.CharField(widget=test_upload_widget)
    upload_form2 = forms.CharField(widget=test_upload_widget2)
