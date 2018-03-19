from django import forms

from jqfileupload.widgets import uploader
from jqfileupload.widgets.uploader import UploadedAjaxFileList

test_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/ulwidget1/"
)
test_upload_widget2 = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/ulwidget2/", multifile=False
)


class UploadForm(forms.Form):
    title = forms.CharField(label="Blah")
    something = forms.CharField(label="Blabl")
    upload_form = UploadedAjaxFileList(widget=test_upload_widget)
    upload_form2 = UploadedAjaxFileList(widget=test_upload_widget2)
