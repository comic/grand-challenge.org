from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django_select2.forms import Select2MultipleWidget

from grandchallenge.blogs.forms import PostUpdateForm
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList
from grandchallenge.products.models import ProjectAirFiles


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


class ProjectAirFilesForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = ProjectAirFiles
        fields = ["title", "study_file", "archive"]


class ProductsPostUpdateForm(PostUpdateForm):
    class Meta(PostUpdateForm.Meta):
        fields = (*PostUpdateForm.Meta.fields, "companies")
        widgets = {
            **PostUpdateForm.Meta.widgets,
            "companies": Select2MultipleWidget,
        }
