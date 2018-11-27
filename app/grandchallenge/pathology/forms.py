from django.forms import ModelForm
from grandchallenge.pathology.models import PatientItem
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study

from django_select2.forms import Select2MultipleWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class PatientItemCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("create", "Create"))

    class Meta:
        model = PatientItem
        fields = [
            "patient",
            "study",
        ]

        widgets = {
            "tudy": Select2MultipleWidget,
        }