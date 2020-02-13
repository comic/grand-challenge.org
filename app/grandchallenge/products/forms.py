from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList


class ImportForm(SaveFormInitMixin, forms.Form):
    products_file = forms.FileField()
    companies_file = forms.FileField()
    images_zip = UploadedAjaxFileList(
        widget=uploader.AjaxUploadWidget(multifile=False, auto_commit=False),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("save", "Submit"))
        self.fields["images_zip"].widget.user = user
