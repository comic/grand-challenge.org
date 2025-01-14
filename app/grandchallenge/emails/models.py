from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from guardian.utils import get_anonymous_user

from grandchallenge.core.models import UUIDModel
from grandchallenge.emails.emails import create_email_object
from grandchallenge.profiles.models import EmailSubscriptionTypes


class Email(models.Model):

    subject = models.CharField(max_length=1024)
    body = models.TextField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)
    status_report = models.JSONField(
        blank=True,
        null=True,
        default=None,
        help_text="This stores the page number of the last successfully sent email batch for this email.",
    )

    class Meta:
        ordering = ["pk"]

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


class RawEmail(UUIDModel):
    message = models.TextField(editable=False)
    errored = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created",)
