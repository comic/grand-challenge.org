from django.forms import ModelForm
from grandchallenge.patients.models import Patient

class PatientCreationForm(ModelForm):
    class Meta:
        model = Patient
        fields = '__all__'
