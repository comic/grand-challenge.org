from django.forms import ModelForm
from django.utils.translation import ugettext_lazy as _

from grandchallenge.patients.models import Patient

class PatientCreationForm(ModelForm):
    class Meta:
        model = Patient
        fields = ['title', 'trunk', 'parent']
