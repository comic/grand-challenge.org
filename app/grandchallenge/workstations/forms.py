from crispy_forms.helper import FormHelper
from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms import (
    ChoiceField,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
)
from guardian.shortcuts import get_objects_for_user

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget
from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)


class WorkstationForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = Workstation
        fields = ("title", "logo", "description", "public")


class WorkstationImageForm(SaveFormInitMixin, ModelForm):
    user_upload = ModelChoiceField(
        widget=UserUploadSingleWidget(),
        label="Workstation Container Image",
        queryset=UserUpload.objects.none(),
        # TODO set validators
        help_text=(
            ".tar.xz archive of the container image produced from the command "
            "'docker save IMAGE | xz -c > IMAGE.tar.xz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
    )
    creator = ModelChoiceField(
        widget=HiddenInput(), queryset=get_user_model().objects.all(),
    )
    workstation = ModelChoiceField(
        widget=HiddenInput(), queryset=Workstation.objects.none(),
    )

    def __init__(self, *args, user, workstation, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user_upload"].queryset = get_objects_for_user(
            user, "change_userupload", UserUpload
        )

        self.fields["creator"].initial = user

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
            "user_upload",
            "creator",
            "workstation",
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
