from django.forms import ModelForm
from grandchallenge.studies.models import Study

class StudyCreationForm(ModelForm):
    class Meta:
        model = Study
        fields = '__all__'
