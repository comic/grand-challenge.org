from django import forms

from grandchallenge.core.forms import SaveFormInitMixin


class ImportForm(SaveFormInitMixin, forms.Form):
    products_file = forms.FileField()
    companies_file = forms.FileField()
    images_zip = forms.FileField()
