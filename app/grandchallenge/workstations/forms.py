from crispy_forms.helper import FormHelper
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import (
    ChoiceField,
    Form,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
)

from grandchallenge.components.forms import ContainerImageForm
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.guardian import filter_by_permission
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

    def __init__(self, *args, reader_study, **kwargs):
        super().__init__(*args, **kwargs)

        self.reader_study = reader_study

        self.helper = FormHelper(self)
        self.helper.attrs.update({"class": "d-none"})

        self.fields["ping_times"].required = False

    def clean(self):
        if self.reader_study and not self.reader_study.is_launchable:
            raise ValidationError("Reader study cannot be launched.")
        return super().clean()

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

    def __init__(self, *args, user, workstation, **kwargs):
        super().__init__(*args, **kwargs)
        self.__user = user
        self.__workstation = workstation
        self.fields["extra_env_vars"].initial = [
            {"name": "LOG_LEVEL", "value": "DEBUG"},
            {"name": "CIRRUS_PROFILING_ENABLED", "value": "True"},
        ]

    def clean(self):
        cleaned_data = super().clean()

        if Session.objects.filter(
            creator=self.__user,
            workstation_image__workstation=self.__workstation,
            status__in=[Session.QUEUED, Session.STARTED, Session.RUNNING],
            region=cleaned_data["region"],
        ).exists():
            raise ValidationError(
                "You already have a running workstation in the selected "
                "region, please wait for that session to finish"
            )

        return cleaned_data

    class Meta:
        model = Session
        fields = ("region", "extra_env_vars")
        widgets = {
            "extra_env_vars": JSONEditorWidget(schema=ENV_VARS_SCHEMA),
        }


class WorkstationImageMoveForm(SaveFormInitMixin, Form):
    workstation_image = ModelChoiceField(
        queryset=WorkstationImage.objects.none(),
        widget=HiddenInput(),
        disabled=True,
    )
    new_active_image = ModelChoiceField(
        queryset=WorkstationImage.objects.none(),
        widget=HiddenInput(),
        disabled=True,
        required=False,
    )
    new_workstation = ModelChoiceField(queryset=Workstation.objects.none())

    def __init__(self, *args, workstation_image, user, **kwargs):
        super().__init__(*args, **kwargs)

        # We only handle executable images here so that the
        # change happens quickly. For support of non-executable
        # images Celery tasks need to be invoked for both the
        # old and new workstation images. See AlgorithmImageActivate.
        workstation_executable_images = (
            WorkstationImage.objects.executable_images()
            .filter(workstation=workstation_image.workstation)
            .order_by("-created")
        )

        self.fields["workstation_image"].queryset = filter_by_permission(
            queryset=workstation_executable_images.filter(
                pk=workstation_image.pk
            ),
            user=user,
            codename="change_workstationimage",
        )
        self.fields["workstation_image"].initial = workstation_image

        new_active_images = filter_by_permission(
            queryset=workstation_executable_images.exclude(
                pk=workstation_image.pk
            ),
            user=user,
            codename="change_workstationimage",
        )
        self.fields["new_active_image"].queryset = new_active_images
        self.fields["new_active_image"].initial = new_active_images.first()

        self.fields["new_workstation"].queryset = filter_by_permission(
            queryset=Workstation.objects.exclude(
                pk=workstation_image.workstation.pk
            ),
            user=user,
            codename="change_workstation",
        )
