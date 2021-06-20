from django.db import models
from django.db.transaction import on_commit

from grandchallenge.webhooks.tasks import get_tarball


class GitHubWebhookMessage(models.Model):
    received_at = models.DateTimeField(help_text="When we received the event.")
    payload = models.JSONField(default=None, null=True)
    tarball = models.FileField(null=True)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding and self.payload.get("ref_type") == "tag":
            on_commit(lambda: get_tarball.apply_async(kwargs={"pk": self.pk}))

    class Meta:
        indexes = [
            models.Index(fields=["received_at"]),
        ]
