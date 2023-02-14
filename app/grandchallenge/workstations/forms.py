from crispy_forms.helper import FormHelper
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import ChoiceField, HiddenInput, ModelChoiceField, ModelForm

from grandchallenge.components.forms import ContainerImageForm
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.workstations.models import (
    ENV_VARS_SCHEMA,
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
        fields = ("region", "ping_times")


class DebugSessionForm(SaveFormInitMixin, ModelForm):
    region = ChoiceField(
        required=True,
        choices=[
            c
            for c in Session.Region.choices
            if c[0] in settings.WORKSTATIONS_ACTIVE_REGIONS
        ],
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.__user = user
        self.fields["extra_env_vars"].initial = [
            {"name": "LOG_LEVEL", "value": "DEBUG"},
            {"name": "CIRRUS_PROFILING_ENABLED", "value": "True"},
        ]

    def clean(self):
        cleaned_data = super().clean()

        if Session.objects.filter(
            creator=self.__user,
            status__in=[Session.QUEUED, Session.STARTED, Session.RUNNING],
            region=cleaned_data["region"],
        ).exists():
            raise ValidationError(
                "You already have a running workstation, please wait for that session to finish"
            )

        return cleaned_data

    class Meta:
        model = Session
        fields = ("region", "extra_env_vars")
        widgets = {
            "extra_env_vars": JSONEditorWidget(schema=ENV_VARS_SCHEMA),
        }
