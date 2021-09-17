from datetime import timedelta

from allauth.account.signals import email_confirmed
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.utils.html import format_html
from pyswot import is_academic

from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.tokens import (
    email_verification_token_generator,
)


def email_is_trusted(*, email):
    return is_academic(email)


class Verification(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    user = models.OneToOneField(
        get_user_model(), unique=True, on_delete=models.CASCADE,
    )

    email = models.EmailField(blank=True)
    email_is_verified = models.BooleanField(default=False, editable=False)
    email_verified_at = models.DateTimeField(
        blank=True, null=True, editable=False
    )

    is_verified = models.BooleanField(default=None, null=True, editable=False)
    verified_at = models.DateTimeField(blank=True, null=True, editable=False)

    def __str__(self):
        return f"Verification for {self.user}"

    @property
    def signup_email(self):
        return self.user.email

    @property
    def signup_email_activated(self):
        return self.user.emailaddress_set.filter(
            verified=True, email=self.signup_email
        ).exists()

    @property
    def signup_email_is_trusted(self):
        return self.signup_email_activated and email_is_trusted(
            email=self.signup_email
        )

    @property
    def token(self):
        return email_verification_token_generator.make_token(self.user)

    @property
    def verification_url(self):
        return reverse("verifications:confirm", kwargs={"token": self.token},)

    @property
    def review_deadline(self):
        return self.modified + timedelta(days=3)

    @property
    def user_info(self):
        return format_html(
            "<span>{} <br/> {} <br/> {} <br/> {} <br/> {}</span>",
            self.user.get_full_name(),
            self.user.user_profile.institution,
            self.user.user_profile.department,
            self.user.user_profile.country,
            self.user.user_profile.website,
        )


def create_verification(email_address, *_, **__):
    if (
        email_is_trusted(email=email_address.email)
        and not Verification.objects.filter(
            Q(user=email_address.user) | Q(email__iexact=email_address.email)
        ).exists()
    ):
        Verification.objects.create(
            user=email_address.user, email=email_address.email
        )


email_confirmed.connect(create_verification)
