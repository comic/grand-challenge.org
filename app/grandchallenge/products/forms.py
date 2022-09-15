from django import forms
from django.forms import ModelChoiceField
from django_select2.forms import Select2MultipleWidget

from grandchallenge.blogs.forms import PostUpdateForm
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.products.models import ProjectAirFiles
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget


class ImportForm(SaveFormInitMixin, forms.Form):
    products_file = ModelChoiceField(
        queryset=None, widget=UserUploadSingleWidget()
    )
    companies_file = ModelChoiceField(
        queryset=None, widget=UserUploadSingleWidget()
    )
    images_zip = ModelChoiceField(
        queryset=None, widget=UserUploadSingleWidget()
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        qs = get_objects_for_user(
            user,
            "uploads.change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)

        for field in ["products_file", "companies_file", "images_zip"]:
            self.fields[field].queryset = qs


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
