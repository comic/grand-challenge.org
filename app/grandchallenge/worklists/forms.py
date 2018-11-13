from django.forms import ModelForm
from grandchallenge.worklists.models import Worklist, WorklistSet


class WorklistSetDetailForm(ModelForm):
    class Meta:
        model = WorklistSet
        fields = ("title",)

class WorklistDetailForm(ModelForm):
    class Meta:
        model = Worklist
        fields = ("title", "set",)
