from django.forms import ModelForm
from grandchallenge.studies.models import Study


class StudyDetailForm(ModelForm):
    class Meta:
        model = Study
        fields = ("id", "code", "region_of_interest")
