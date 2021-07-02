from django.db import models

from grandchallenge.core.models import UUIDModel


class Build(UUIDModel):
    build_id = models.CharField(max_length=1024)
    project_name = models.CharField(max_length=1024)
    status = models.CharField(blank=True, max_length=256)
    build_log = models.JSONField(null=True)
    build_config = models.JSONField()
    webhook_message = models.ForeignKey(
        "github.GitHubWebhookMessage", on_delete=models.SET_NULL, null=True
    )
    algorithm = models.ForeignKey(
        "algorithms.Algorithm", on_delete=models.SET_NULL, null=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["build_id"]),
        ]
