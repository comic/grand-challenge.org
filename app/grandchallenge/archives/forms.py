from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import (
    ChoiceField,
    Form,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
    TextInput,
)
from guardian.utils import get_anonymous_user

from grandchallenge.archives.models import Archive
from grandchallenge.core.forms import (
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.widgets import MarkdownEditorWidget


class ArchiveForm(WorkstationUserFilterMixin, SaveFormInitMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].required = True
        self.fields["workstation"].required = True

    class Meta:
        model = Archive
        fields = (
            "title",
            "description",
            "logo",
            "workstation",
            "workstation_config",
            "detail_page_markdown",
        )
        widgets = {
            "description": TextInput,
            "detail_page_markdown": MarkdownEditorWidget,
        }


class UserGroupForm(SaveFormInitMixin, Form):
    ADD = "ADD"
    REMOVE = "REMOVE"
    CHOICES = ((ADD, "Add"), (REMOVE, "Remove"))
    user = ModelChoiceField(
        queryset=get_user_model().objects.all().order_by("username"),
        help_text="Select a user that will be added to the group",
        required=True,
        widget=autocomplete.ModelSelect2(
            url="archives:users-autocomplete",
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

    def add_or_remove_user(self, *, archive):
        if self.cleaned_data["action"] == self.ADD:
            getattr(archive, f"add_{self.role}")(self.cleaned_data["user"])
        elif self.cleaned_data["action"] == self.REMOVE:
            getattr(archive, f"remove_{self.role}")(self.cleaned_data["user"])


class EditorsForm(UserGroupForm):
    role = "editor"


class UsersForm(UserGroupForm):
    role = "user"
