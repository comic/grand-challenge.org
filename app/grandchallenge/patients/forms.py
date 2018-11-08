from django.forms import ModelForm
from grandchallenge.patients.models import Patient


class PatientDetailForm(ModelForm):
    class Meta:
        model = Patient
        fields = ("id", "name", "sex", "height")
