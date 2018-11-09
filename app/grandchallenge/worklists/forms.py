from django.forms import ModelForm
from grandchallenge.worklists.models import WorklistSet

class WorklistSetDetailForm(ModelForm):
    class Meta:
        model = WorklistSet
        fields = ("title",)