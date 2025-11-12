import logging

import boto3
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.components.backends.utils import LOGLINES
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import copy_s3_object
from grandchallenge.github.models import GitHubWebhookMessage

logger = logging.getLogger(__name__)


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
        choices=BuildStatusChoices,
        max_length=11,
        default=BuildStatusChoices.IN_PROGRESS,
    )
    build_log = models.TextField(blank=True)

    BuildStatusChoices = BuildStatusChoices

    __codebuild_client = None
    __logs_client = None
    __s3_client = None

    @property
    def codebuild_client(self):
        if self.__codebuild_client is None:
            self.__codebuild_client = boto3.client(
                "codebuild", region_name=settings.AWS_CODEBUILD_REGION_NAME
            )
        return self.__codebuild_client

    @property
    def _logs_client(self):
        if self.__logs_client is None:
            self.__logs_client = boto3.client(
                "logs", region_name=settings.AWS_CODEBUILD_REGION_NAME
            )
        return self.__logs_client

    @property
    def _s3_client(self):
        if self.__s3_client is None:
            self.__s3_client = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            )
        return self.__s3_client

    @property
    def build_number(self):
        return self.build_id.split(":")[-1]

    def refresh_logs(self):
        boto3.client("logs", region_name=settings.COMPONENTS_AMAZON_ECR_REGION)

        response = self._logs_client.get_log_events(
            logGroupName=settings.CODEBUILD_BUILD_LOGS_GROUP_NAME,
            logStreamName=self.build_number,
            limit=LOGLINES,
            startFromHead=False,
        )

        self.build_log = "".join(
            event["message"]
            for event in response["events"]
            if not event["message"].startswith("[Container]")
        )

    def add_image_to_algorithm(self):
        copy_s3_object(
            to_field=self.algorithm_image.image,
            dest_filename=f"{self.pk}.tar.gz",
            src_bucket=settings.CODEBUILD_ARTIFACTS_BUCKET_NAME,
            src_key=f"codebuild/artifacts/{self.build_number}/{self.build_config['projectName']}/container-image.tar.gz",
            mimetype="application/gzip",
            save=True,
        )

    def delete_artifacts(self):
        bucket = settings.CODEBUILD_ARTIFACTS_BUCKET_NAME
        prefix = f"codebuild/artifacts/{self.build_number}"

        objects_list = self._s3_client.list_objects_v2(
            Bucket=bucket, Prefix=prefix
        )

        if contents := objects_list.get("Contents"):
            response = self._s3_client.delete_objects(
                Bucket=settings.CODEBUILD_ARTIFACTS_BUCKET_NAME,
                Delete={
                    "Objects": [
                        {"Key": content["Key"]} for content in contents
                    ],
                },
            )
            logger.debug(f"Deleted {response.get('Deleted')} from {bucket}")
            errors = response.get("Errors")
        else:
            logger.debug(f"No objects found in {bucket}/{prefix}")
            errors = None

        if objects_list["IsTruncated"] or errors:
            logger.error("Not all files were deleted")

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

        build_data = self.codebuild_client.start_build(**self.build_config)

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
    def finished(self):
        return self.status != BuildStatusChoices.IN_PROGRESS

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
        indexes = [models.Index(fields=["build_id"])]
