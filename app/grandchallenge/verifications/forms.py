import logging

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.html import format_html
from pyswot.pyswot import _domain_parts, _is_stoplisted

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.profiles.tasks import deactivate_user
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import Verification
from grandchallenge.verifications.resources.free_email_domains import (
    FREE_EMAIL_DOMAINS,
)
from grandchallenge.verifications.tokens import (
    email_verification_token_generator,
)

logger = logging.getLogger(__name__)


class VerificationForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields["user"].queryset = get_user_model().objects.filter(
            pk=self.user.pk
        )
        self.fields["user"].initial = self.user
        self.fields["user"].widget = forms.HiddenInput()

        self.fields["email"].initial = self.user.email
        self.fields["email"].required = True
        self.fields[
            "email"
        ].help_text = (
            "Please provide your work, corporate or institutional email"
        )

    def clean_email(self):
        email = self.cleaned_data["email"]
        email = BaseUserManager.normalize_email(email)

        domain = email.split("@")[1].lower()

        if domain in FREE_EMAIL_DOMAINS or "wecom" in domain:
            raise ValidationError(
                f"Email hosted by {domain} cannot be used for verification, "
                "please provide your work, corporate or institutional email."
            )

        if domain in settings.DISALLOWED_EMAIL_DOMAINS or _is_stoplisted(
            _domain_parts(email)
        ):
            raise ValidationError(
                f"Email hosted by {domain} cannot be used for verification "
                "due to abuse. Please send an email to support@grand-challenge.org "
                "with your user name, institutional email address and a link to your "
                "Google Scholar account, lab page, research gate profile "
                "or similar so your email address can be verified."
            )

        if (
            get_user_model()
            .objects.filter(email__iexact=email)
            .exclude(pk=self.user.pk)
            .exists()
            or Verification.objects.filter(email__iexact=email).exists()
        ):
            raise ValidationError("This email is already in use")

        return email

    def clean(self):
        if self.user.user_profile.is_incomplete:
            profile_link = reverse(
                "profile-update", kwargs={"username": self.user.username}
            )
            raise ValidationError(
                format_html(
                    (
                        "Your profile information is incomplete. You can complete "
                        "your profile <a href='{}'>here</a>."
                    ),
                    profile_link,
                )
            )
        try:
            if self.user.verification:
                raise ValidationError(
                    "You have already made a verification request"
                )
        except ObjectDoesNotExist:
            pass

    class Meta:
        model = Verification
        fields = ("user", "email")


class ConfirmEmailForm(SaveFormInitMixin, forms.Form):
    token = forms.CharField(
        help_text="Your email confirmation token", disabled=True
    )

    def __init__(self, *args, user, token, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["token"].initial = token
        self.user = user

    def clean_token(self):
        token = self.cleaned_data["token"]

        if not hasattr(self.user, "verification"):
            deactivate_user.signature(
                kwargs={"user_pk": self.user.pk}
            ).apply_async()
            logger.error(
                f"{self.user} was deactivated for using verification {token}"
                "which does not belong to them."
            )
            raise ValidationError("Token is invalid")

        if not email_verification_token_generator.check_token(
            self.user, token
        ):
            logger.error(
                f"{self.user} used invalid verification token {token}."
            )
            raise ValidationError("Token is invalid")

        return token
