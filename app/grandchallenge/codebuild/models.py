from django.db import models
from django.utils.text import get_valid_filename

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import private_s3_storage


def log_path(instance, filename):

    return (
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class Build(UUIDModel):
    build_id = models.CharField(max_length=1024)
    project_name = models.CharField(max_length=1024)
    status = models.CharField(blank=True, max_length=256)
    build_log = models.FileField(
        null=True, upload_to=log_path, storage=private_s3_storage
    )
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
