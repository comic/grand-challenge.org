from django.contrib.auth import get_user_model
from django.db import models
from django.utils.timezone import now
from pyswot import is_academic

from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.tokens import (
    email_verification_token_generator,
)


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
        return self.user.userena_signup.activation_completed

    @property
    def signup_email_is_trusted(self):
        return self.signup_email_activated and self._email_is_trusted(
            self.signup_email
        )

    @property
    def verification_email_is_trusted(self):
        return self.email_is_verified and self._email_is_trusted(self.email)

    @staticmethod
    def _email_is_trusted(email):
        return is_academic(email)

    @property
    def token(self):
        return email_verification_token_generator.make_token(self.user)

    @property
    def verification_url(self):
        return reverse("verifications:confirm", kwargs={"token": self.token},)

    def save(self, *args, **kwargs):
        if self.signup_email_is_trusted or self.verification_email_is_trusted:
            self.is_verified = True
            self.verified_at = now()

        super().save(*args, **kwargs)
