from django.db import models


class GitHubWebhookMessage(models.Model):
    received_at = models.DateTimeField(help_text="When we received the event.")
    payload = models.JSONField(default=None, null=True)
    tarball = models.FileField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=["received_at"]),
        ]
