from dal import autocomplete
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from guardian.utils import get_anonymous_user

from grandchallenge.admins.emails import send_new_admin_notification_email
from grandchallenge.challenges.models import Challenge


class AdminsForm(forms.Form):
    ADD = "ADD"
    REMOVE = "REMOVE"
    CHOICES = ((ADD, "Add admin"), (REMOVE, "Remove admin"))
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all().order_by("username"),
        help_text=(
            "Select a user that will be added to the admins group for "
            "this challenge. This user will have the ability to completely "
            "manage this challenge, including updating the site, deleting "
            "pages, etc."
        ),
        required=True,
        widget=autocomplete.ModelSelect2(
            url="/admins/update-autocomplete",
            attrs={
                "data-placeholder": "Search for a user ...",
                "data-minimum-input-length": 3,
                "data-theme": settings.CRISPY_TEMPLATE_PACK,
            },
        ),
    )

    action = forms.ChoiceField(
        choices=CHOICES, required=True, widget=forms.HiddenInput(), initial=ADD
    )

    def clean_user(self):
        user = self.cleaned_data["user"]
        if user == get_anonymous_user():
            raise ValidationError("You cannot add this user as an admin!")

        return user

    def add_or_remove_user(self, *, challenge: Challenge, site):
        if self.cleaned_data["action"] == AdminsForm.ADD:
            challenge.add_admin(self.cleaned_data["user"])
            send_new_admin_notification_email(
                challenge=challenge,
                new_admin=self.cleaned_data["user"],
                site=site,
            )
        elif self.cleaned_data["action"] == AdminsForm.REMOVE:
            challenge.remove_admin(self.cleaned_data["user"])
