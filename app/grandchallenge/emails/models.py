from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from guardian.utils import get_anonymous_user

from grandchallenge.core.models import UUIDModel
from grandchallenge.emails.emails import create_email_object
from grandchallenge.profiles.models import EmailSubscriptionTypes


class EmailStatusChoices(models.TextChoices):
    INITIALIZED = "INITIALIZED", "Initialized"
    QUEUED = "QUEUED", "Queued"
    SUCCEEDED = "SUCCEEDED", "Succeeded"


class Email(models.Model):
    EmailStatusChoices = EmailStatusChoices

    subject = models.CharField(max_length=1024)
    body = models.TextField()
    status = models.CharField(
        max_length=11,
        choices=EmailStatusChoices,
        default=EmailStatusChoices.INITIALIZED,
    )
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["pk"]
        indexes = [
            models.Index(
                fields=[
                    "status",
                ]
            ),
        ]
        constraints = (
            models.CheckConstraint(
                condition=models.Q(status__in=EmailStatusChoices.values),
                name="%(app_label)s_%(class)s_status_in_choices",
            ),
        )

    def __str__(self):
        return self.subject

    @property
    def rendered_body(self):
        email = create_email_object(
            recipient=get_anonymous_user(),
            site=Site.objects.get_current(),
            subject=self.subject,
            markdown_message=self.body,
            subscription_type=EmailSubscriptionTypes.SYSTEM,
            connection=None,
        )
        alternatives = [
            alternative
            for alternative in email.alternatives
            if alternative[1] == "text/html"
        ]
        return alternatives[0][0]

    def get_absolute_url(self):
        return reverse("emails:detail", kwargs={"pk": self.pk})


class RawEmailStatusChoices(models.TextChoices):
    INITIALIZED = "INITIALIZED", "Initialized"
    QUEUED = "QUEUED", "Queued"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class RawEmail(UUIDModel):
    RawEmailStatusChoices = RawEmailStatusChoices

    message = models.TextField(editable=False)
    status = models.CharField(
        max_length=11,
        choices=RawEmailStatusChoices,
        default=RawEmailStatusChoices.INITIALIZED,
    )

    class Meta:
        ordering = ("-created",)
        indexes = [
            models.Index(
                fields=[
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "-created",
                ]
            ),
        ]
        constraints = (
            models.CheckConstraint(
                condition=models.Q(status__in=RawEmailStatusChoices.values),
                name="%(app_label)s_%(class)s_status_in_choices",
            ),
        )
