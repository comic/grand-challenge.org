from datetime import timedelta

from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.utils.html import format_html
from pyswot import is_academic

from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.tokens import (
    email_verification_token_generator,
)


class Verification(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    user = models.OneToOneField(
        get_user_model(), unique=True, on_delete=models.CASCADE
    )

    email = models.EmailField(unique=True)
    email_is_verified = models.BooleanField(default=False, editable=False)
    email_verified_at = models.DateTimeField(
        blank=True, null=True, editable=False
    )

    is_verified = models.BooleanField(default=None, null=True, editable=False)
    verified_at = models.DateTimeField(blank=True, null=True, editable=False)

    def __str__(self):
        return f"Verification for {self.user}"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if (
            adding
            and EmailAddress.objects.filter(
                user=self.user, email=self.email, verified=True
            ).exists()
        ):
            self.email_is_verified = True

        super().save(*args, **kwargs)

        if adding and not self.email_is_verified:
            self.send_verification_email()

    @property
    def token(self):
        return email_verification_token_generator.make_token(self.user)

    @property
    def verification_url(self):
        return reverse("verifications:confirm", kwargs={"token": self.token})

    @property
    def review_deadline(self):
        return self.modified + timedelta(
            days=settings.VERIFICATIONS_REVIEW_PERIOD_DAYS
        )

    @property
    def verification_badge(self):
        if self.is_verified:
            return format_html(
                '<i class="fas fa-user-check text-success" '
                'title="Verified email address at {}"></i>',
                self.email.split("@")[1],
            )
        else:
            return ""

    def send_verification_email(self):
        if self.email_is_verified:
            # Nothing to do
            return

        site = Site.objects.get_current()
        message = (
            f"Dear {self.user.username},\n\n"
            "Please confirm this email address for account validation by visiting the following link: "
            f"{self.verification_url}\n\n"
            "Please disregard this email if you did not make this validation request.\n\n"
            "Regards,\n"
            f"{site.name}\n"
            f"This is an automated service email from {site.domain}."
        )
        send_mail(
            subject=f"[{site.domain.lower()}] Please confirm your email address for account validation",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            message=message,
        )


def create_verification(email_address, *_, **__):
    if (
        is_academic(email=email_address.email)
        and not Verification.objects.filter(
            Q(user=email_address.user) | Q(email__iexact=email_address.email)
        ).exists()
    ):
        Verification.objects.create(
            user=email_address.user, email=email_address.email
        )


email_confirmed.connect(create_verification)


class VerificationUserSet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    users = models.ManyToManyField(
        get_user_model(), through="VerificationUserSetUser"
    )

    def get_absolute_url(self):
        return reverse(
            "verifications:verification-user-set-detail",
            kwargs={"pk": self.pk},
        )


class VerificationUserSetUser(models.Model):
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    user_set = models.ForeignKey(VerificationUserSet, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
