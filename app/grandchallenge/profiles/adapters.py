from allauth.account.adapter import DefaultAccountAdapter
from django import forms

from config import settings


class AccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        email = super().clean_email(email=email)

        domain = email.split("@")[1].lower()

        if domain in settings.DISALLOWED_EMAIL_DOMAINS:
            raise forms.ValidationError(
                f"Email addresses hosted by {domain} cannot be used."
            )

        return email
