from django.forms import ModelForm

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.workstation_configs.models import WorkstationConfig


class WorkstationConfigForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = WorkstationConfig
        exclude = ("creator",)
