from datetime import timedelta

from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.html import format_html
from pyswot import is_academic, is_free

from grandchallenge.core.models import FieldChangeMixin
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import (
    BannedEmailAddress,
    EmailSubscriptionTypes,
)
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.tokens import (
    email_verification_token_generator,
)


class Verification(FieldChangeMixin, models.Model):
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

    def clean(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)

        self.email = clean_email(email=self.email)

        if is_free(self.email):
            raise ValidationError(
                "Email hosted on this domain cannot be used for verification, "
                "please provide your work, corporate or institutional email."
            )

        if (
            get_user_model()
            .objects.filter(email__iexact=self.email)
            .exclude(pk=self.user.pk)
            .exists()
            or EmailAddress.objects.filter(email__iexact=self.email)
            .exclude(user=self.user)
            .exists()
        ):
            raise ValidationError("This email is already in use.")

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

        if self.has_changed("is_verified") and self.is_verified:
            self.accept_pending_requests_for_verified_users()

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

        message = format_html(
            (
                "Please confirm this email address for account validation by "
                "visiting the following link: [{url}]({url}) \n\n"
                "Please disregard this email if you did not make this validation request."
            ),
            url=self.verification_url,
        )
        site = Site.objects.get_current()
        send_standard_email_batch(
            site=site,
            subject="Please confirm your email address for account validation",
            markdown_message=message,
            recipients=[self.user],
            subscription_type=EmailSubscriptionTypes.SYSTEM,
            user_email_override={self.user: self.email},
        )

    def accept_pending_requests_for_verified_users(self):
        from grandchallenge.algorithms.models import AlgorithmPermissionRequest
        from grandchallenge.archives.models import ArchivePermissionRequest
        from grandchallenge.participants.models import RegistrationRequest
        from grandchallenge.reader_studies.models import (
            ReaderStudyPermissionRequest,
        )

        if not self.is_verified:
            raise RuntimeError(
                "Refusing to accept verifications for unverified user"
            )

        permission_request_classes = {
            "algorithm": AlgorithmPermissionRequest,
            "archive": ArchivePermissionRequest,
            "reader_study": ReaderStudyPermissionRequest,
            "challenge": RegistrationRequest,
        }

        for (
            object_name,
            request_class,
        ) in permission_request_classes.items():
            for request_object in request_class.objects.filter(
                **{
                    "user": self.user,
                    "status": request_class.PENDING,
                    f"{object_name}__access_request_handling": AccessRequestHandlingOptions.ACCEPT_VERIFIED_USERS,
                }
            ):
                request_object.status = request_class.ACCEPTED
                request_object.save()


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
    auto_deactivate = models.BooleanField(
        default=False,
        help_text="Whether to automatically deactivate users added to this set",
    )
    is_false_positive = models.BooleanField(
        default=False,
        help_text="If this set was created in error",
    )
    comment = models.TextField(blank=True)

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

    class Meta:
        unique_together = (("user_set", "user"),)


def clean_email(*, email):
    """
    Email addresses that cannot be used throughout the site

    This includes sign-up, verification, and password reset. Here,
    we want to allow free email domains.
    """
    email = get_user_model().objects.normalize_email(email)

    domain = email.split("@")[1].lower()

    if domain in settings.DISALLOWED_EMAIL_DOMAINS or "wecom" in domain:
        raise ValidationError(
            f"Email addresses hosted by {domain} cannot be used."
        )

    if Verification.objects.filter(email__iexact=email).exists():
        raise ValidationError("This email address is already in use.")

    if BannedEmailAddress.objects.filter(email__iexact=email).exists():
        raise ValidationError("This email address is not allowed.")

    return email
