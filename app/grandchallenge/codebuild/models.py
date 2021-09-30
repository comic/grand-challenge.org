import gzip
from tempfile import NamedTemporaryFile

import boto3
from django.conf import settings
from django.core import files
from django.db import models
from django.utils.translation import gettext_lazy as _

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import private_s3_storage
from grandchallenge.github.models import GitHubWebhookMessage


class BuildStatusChoices(models.TextChoices):
    """From https://docs.aws.amazon.com/codebuild/latest/APIReference/API_Build.html"""

    SUCCEEDED = "SUCCEEDED", _("Succeeded")
    FAILED = "FAILED", _("Failed")
    FAULT = "FAULT", _("Fault")
    TIMED_OUT = "TIMED_OUT", _("Timed Out")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    STOPPED = "STOPPED", _("Stopped")


class Build(UUIDModel):
    webhook_message = models.ForeignKey(
        GitHubWebhookMessage, on_delete=models.SET_NULL, null=True
    )
    algorithm_image = models.OneToOneField(
        AlgorithmImage, on_delete=models.SET_NULL, null=True
    )
    build_config = models.JSONField()
    build_id = models.CharField(max_length=1024)
    status = models.CharField(
        choices=BuildStatusChoices.choices, max_length=11
    )
    build_log = models.TextField(blank=True)

    BuildStatusChoices = BuildStatusChoices
    __client = None

    @property
    def client(self):
        if self.__client is None:
            self.__client = boto3.client("codebuild")
        return self.__client

    @property
    def build_number(self):
        return self.build_id.split(":")[-1]

    def refresh_status(self):
        build_statuses = self.client.batch_get_builds(ids=[self.build_id])
        self.status = build_statuses["builds"][0]["buildStatus"]

    def refresh_logs(self):
        with private_s3_storage.open(
            f"codebuild/logs/{self.build_number}.gz"
        ) as file:
            self.build_log = gzip.open(file).read().decode("utf-8")

    def add_image_to_algorithm(self):
        with private_s3_storage.open(
            f"codebuild/artifacts/{self.build_number}/{self.build_config['projectName']}/container-image.tar.gz"
        ) as file:
            with NamedTemporaryFile(delete=True) as tmp_file:
                with open(tmp_file.name, "wb") as fd:
                    for chunk in file.chunks():
                        fd.write(chunk)

                tmp_file.flush()
                temp_file = files.File(
                    tmp_file, name=f"{str(self.pk)}.tar.gz",
                )

                self.algorithm_image.image = temp_file
                self.algorithm_image.save()

    def _create_build(self):
        self.build_config = {
            "projectName": settings.CODEBUILD_PROJECT_NAME,
            "sourceLocationOverride": f"{settings.PRIVATE_S3_STORAGE_KWARGS['bucket_name']}/{self.webhook_message.zipfile.name}",
            "sourceTypeOverride": "S3",
            "environmentVariablesOverride": [
                {
                    "name": "IMAGE_REPO_NAME",
                    "value": f"{AlgorithmImage._meta.app_label}/{AlgorithmImage._meta.model_name}",
                },
                {"name": "IMAGE_TAG", "value": str(self.algorithm_image.pk)},
            ],
        }

        build_data = self.client.start_build(**self.build_config)

        self.build_id = build_data["build"]["id"]
        self.status = build_data["build"]["buildStatus"]

    def save(self, *args, **kwargs):
        if self._state.adding:
            self._create_build()

        super().save(*args, **kwargs)

    @property
    def animate(self):
        return self.status == BuildStatusChoices.IN_PROGRESS

    @property
    def status_context(self):
        if self.status == BuildStatusChoices.SUCCEEDED:
            return "success"
        elif self.status in {BuildStatusChoices.STOPPED}:
            return "warning"
        elif self.status in {
            BuildStatusChoices.FAILED,
            BuildStatusChoices.FAULT,
            BuildStatusChoices.TIMED_OUT,
        }:
            return "danger"
        elif self.status in {BuildStatusChoices.IN_PROGRESS}:
            return "info"
        else:
            return "secondary"

    class Meta:
        indexes = [
            models.Index(fields=["build_id"]),
        ]
