from django.forms import ModelForm
from grandchallenge.worklists.models import Group, Worklist

class GroupCreationForm(ModelForm):
    class Meta:
        model = Group
        fields = '__all__'


class WorklistCreationForm(ModelForm):
    class Meta:
        model = Worklist
        fields = '__all__'
