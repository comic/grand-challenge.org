from django.contrib.auth import get_user_model
from django.db import models
from django.utils.timezone import now
from guardian.shortcuts import assign_perm
from pyswot import is_academic

from grandchallenge.subdomains.utils import reverse


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

    is_verified = models.BooleanField(default=False, editable=False)
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
        return self.signup_email_activated and is_academic(self.signup_email)

    @property
    def verification_email_is_trusted(self):
        return self.email_is_verified and is_academic(self.email)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if self.signup_email_is_trusted or self.verification_email_is_trusted:
            self.is_verified = True
            self.verified_at = now()

        super().save(*args, **kwargs)

        if adding:
            assign_perm("view_verification", self.user, self)

    def get_absolute_url(self):
        return reverse(
            "verifications:detail", kwargs={"username": self.user.username}
        )
