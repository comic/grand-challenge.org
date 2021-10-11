from crispy_forms.helper import FormHelper
from django.conf import settings
from django.forms import (
    ChoiceField,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
)

from grandchallenge.components.forms import ContainerImageForm
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)


class WorkstationForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = Workstation
        fields = ("title", "logo", "description", "public")


class WorkstationImageForm(ContainerImageForm):
    workstation = ModelChoiceField(widget=HiddenInput(), queryset=None)

    def __init__(self, *args, workstation, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["workstation"].queryset = Workstation.objects.filter(
            pk=workstation.pk
        )
        self.fields["workstation"].initial = workstation

    class Meta:
        model = WorkstationImage
        fields = (
            "initial_path",
            "http_port",
            "websocket_port",
            "workstation",
            *ContainerImageForm.Meta.fields,
        )


class SessionForm(ModelForm):
    region = ChoiceField(
        required=True,
        choices=[
            c
            for c in Session.Region.choices
            if c[0] in settings.WORKSTATIONS_ACTIVE_REGIONS
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.attrs.update({"class": "d-none"})

        self.fields["ping_times"].required = False

    class Meta:
        model = Session
        fields = (
            "region",
            "ping_times",
        )
