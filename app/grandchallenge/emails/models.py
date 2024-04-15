from django.db import models
from django.urls import reverse

from grandchallenge.core.models import UUIDModel


class Email(models.Model):

    subject = models.CharField(max_length=1024)
    body = models.TextField(
        help_text="Email body will be prepended with 'Dear [username],' and will end with 'Kind regards, Grand Challenge team' and a link to unsubscribe from the mailing list."
    )
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

    def get_absolute_url(self):
        return reverse("emails:detail", kwargs={"pk": self.pk})


class RawEmail(UUIDModel):
    message = models.TextField(editable=False)
    errored = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created",)
