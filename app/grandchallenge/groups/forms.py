from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import ChoiceField, Form, HiddenInput, ModelChoiceField
from guardian.utils import get_anonymous_user

from grandchallenge.core.forms import SaveFormInitMixin


class UserGroupForm(SaveFormInitMixin, Form):
    role = None
    user_complete_url = "users-autocomplete"

    ADD = "ADD"
    REMOVE = "REMOVE"
    CHOICES = ((ADD, "Add"), (REMOVE, "Remove"))

    user = ModelChoiceField(
        queryset=get_user_model().objects.all().order_by("username"),
        required=True,
        widget=autocomplete.ModelSelect2(
            attrs={
                "data-placeholder": "Search for a user ...",
                "data-minimum-input-length": 3,
                "data-theme": settings.CRISPY_TEMPLATE_PACK,
                "data-html": True,
            },
        ),
    )

    action = ChoiceField(
        choices=CHOICES, required=True, widget=HiddenInput(), initial=ADD
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_field = self.fields["user"]
        user_field.help_text = (
            f"Select a user that will be added as {self.role}"
        )
        user_field.widget.url = self.user_complete_url

    def clean_user(self):
        user = self.cleaned_data["user"]
        if user == get_anonymous_user():
            raise ValidationError("You cannot add this user!")
        return user

    def add_or_remove_user(self, *, obj):
        if self.cleaned_data["action"] == self.ADD:
            getattr(obj, f"add_{self.role}")(self.cleaned_data["user"])
        elif self.cleaned_data["action"] == self.REMOVE:
            getattr(obj, f"remove_{self.role}")(self.cleaned_data["user"])


class EditorsForm(UserGroupForm):
    role = "editor"


class MembersForm(UserGroupForm):
    role = "member"


class UsersForm(UserGroupForm):
    role = "user"
