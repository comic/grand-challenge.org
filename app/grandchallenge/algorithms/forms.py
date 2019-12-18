from crispy_forms.helper import FormHelper
from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import (
    ChoiceField,
    Form,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
)
from guardian.shortcuts import get_objects_for_user
from guardian.utils import get_anonymous_user

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
)
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList
from grandchallenge.workstations.models import Workstation


class AlgorithmForm(SaveFormInitMixin, ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workstation"].queryset = get_objects_for_user(
            user,
            f"{Workstation._meta.app_label}.view_{Workstation._meta.model_name}",
            Workstation,
        )

    class Meta:
        model = Algorithm
        fields = (
            "title",
            "description",
            "logo",
            "visible_to_public",
            "workstation",
            "workstation_config",
            "contact_information",
            "info_url",
            "additional_information",
            "additional_terms",
        )


class AlgorithmImageForm(ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=uploader.AjaxUploadWidget(multifile=False),
        label="Algorithm Image",
        validators=[
            ExtensionValidator(allowed_extensions=(".tar", ".tar.gz"))
        ],
        help_text=(
            ".tar.gz archive of the container image produced from the command "
            "'docker save IMAGE | gzip -c > IMAGE.tar.gz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.fields["chunked_upload"].widget.user = user

    class Meta:
        model = AlgorithmImage
        fields = ("requires_gpu", "chunked_upload")


class AlgorithmImageUpdateForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = AlgorithmImage
        fields = ("requires_gpu",)


class UserGroupForm(SaveFormInitMixin, Form):
    ADD = "ADD"
    REMOVE = "REMOVE"
    CHOICES = ((ADD, "Add"), (REMOVE, "Remove"))
    user = ModelChoiceField(
        queryset=get_user_model().objects.all().order_by("username"),
        help_text="Select a user that will be added to the group",
        required=True,
        widget=autocomplete.ModelSelect2(
            url="algorithms:users-autocomplete",
            attrs={
                "data-placeholder": "Search for a user ...",
                "data-minimum-input-length": 3,
                "data-theme": settings.CRISPY_TEMPLATE_PACK,
            },
        ),
    )
    action = ChoiceField(
        choices=CHOICES, required=True, widget=HiddenInput(), initial=ADD
    )

    def clean_user(self):
        user = self.cleaned_data["user"]
        if user == get_anonymous_user():
            raise ValidationError("You cannot add this user!")
        return user

    def add_or_remove_user(self, *, algorithm):
        if self.cleaned_data["action"] == self.ADD:
            getattr(algorithm, f"add_{self.role}")(self.cleaned_data["user"])
        elif self.cleaned_data["action"] == self.REMOVE:
            getattr(algorithm, f"remove_{self.role}")(
                self.cleaned_data["user"]
            )


class EditorsForm(UserGroupForm):
    role = "editor"


class UsersForm(UserGroupForm):
    role = "user"

    def add_or_remove_user(self, *args, algorithm):
        super().add_or_remove_user(algorithm=algorithm)
        user = self.cleaned_data["user"]
        try:
            permission_request = AlgorithmPermissionRequest.objects.get(
                user=user, algorithm=algorithm
            )
        except ObjectDoesNotExist:
            return
        if self.cleaned_data["action"] == self.REMOVE:
            permission_request.status = AlgorithmPermissionRequest.REJECTED
        else:
            permission_request.status = AlgorithmPermissionRequest.ACCEPTED
        permission_request.save()
