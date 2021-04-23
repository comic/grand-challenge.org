import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import on_commit
from guardian.shortcuts import assign_perm

from config.celery import celery_app
from grandchallenge.core.models import UUIDModel
from grandchallenge.evaluation.models import Phase
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workspaces.crypters import FernetCrypter


class ProviderChoices(models.TextChoices):
    INTERNAL = "INTERNAL", "Internal"


class WorkbenchToken(models.Model):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        editable=False,
        related_name="workbench_token",
    )
    email = models.EmailField(editable=False)
    _token = models.TextField(db_column="token", editable=False)
    provider = models.CharField(
        max_length=8,
        choices=ProviderChoices.choices,
        default=ProviderChoices.INTERNAL,
        editable=False,
    )

    def __str__(self):
        return f"{self.user}"

    @property
    def token(self):
        if settings.WORKBENCH_SECRET_KEY:
            return FernetCrypter().decrypt(
                encoded=self._token, secret_key=settings.WORKBENCH_SECRET_KEY
            )
        else:
            raise RuntimeError("WORKBENCH_SECRET_KEY is not set")

    @token.setter
    def token(self, value):
        if settings.WORKBENCH_SECRET_KEY:
            self._token = FernetCrypter().encrypt(
                data=value, secret_key=settings.WORKBENCH_SECRET_KEY
            )
        else:
            raise RuntimeError("WORKBENCH_SECRET_KEY is not set")


class WorkspaceKindChoices(models.TextChoices):
    SAGEMAKER_NOTEBOOK = "SAGEMAKER_NOTEBOOK", "SageMaker Notebook"
    EC2_LINUX = "EC2_LINUX", "EC2 Linux"


class WorkspaceTypeConfiguration(models.Model):
    service_workbench_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    instance_type = models.CharField(max_length=16)
    auto_stop_time = models.PositiveSmallIntegerField(default=10)
    kind = models.CharField(
        max_length=18, choices=WorkspaceKindChoices.choices
    )
    enabled_phases = models.ManyToManyField(
        Phase, blank=True, related_name="enabled_workspace_type_configurations"
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            on_commit(
                lambda: celery_app.signature(
                    "grandchallenge.workspaces.tasks.create_workspace_type_configuration"
                ).apply_async(
                    kwargs={"workspace_type_configuration_pk": self.pk}
                )
            )

    @property
    def name(self):
        return f"{self.get_kind_display()} {self.instance_type} with {self.auto_stop_time} minute timeout".replace(
            ".", "-"
        )

    @property
    def params(self):
        if self.kind == WorkspaceKindChoices.SAGEMAKER_NOTEBOOK:
            return [
                {"key": "EncryptionKeyArn", "value": "${encryptionKeyArn}"},
                {"key": "IamPolicyDocument", "value": "${iamPolicyDocument}"},
                {"key": "VPC", "value": "${vpcId}"},
                {"key": "AccessFromCIDRBlock", "value": "${cidr}"},
                {
                    "key": "EnvironmentInstanceFiles",
                    "value": "${environmentInstanceFiles}",
                },
                {"key": "InstanceType", "value": self.instance_type},
                {"key": "Subnet", "value": "${subnetId}"},
                {"key": "S3Mounts", "value": "${s3Mounts}"},
                {"key": "Namespace", "value": "${namespace}"},
                {
                    "key": "AutoStopIdleTimeInMinutes",
                    "value": self.auto_stop_time,
                },
            ]
        else:
            raise NotImplementedError

    ALLOWED_INSTANCE_TYPES = {
        # From https://aws.amazon.com/sagemaker/pricing/
        WorkspaceKindChoices.SAGEMAKER_NOTEBOOK: {
            "ml.t3.medium",
            "ml.t3.large",
            "ml.t3.xlarge",
            "ml.t3.2xlarge",
            "ml.m5.xlarge",
            "ml.m5.2xlarge",
            "ml.m5.4xlarge",
            "ml.m5.12xlarge",
            "ml.m5.24xlarge",
            "ml.c5.xlarge",
            "ml.c5.2xlarge",
            "ml.c5.4xlarge",
            "ml.c5.9xlarge",
            "ml.c5.18xlarge",
            "ml.c5d.xlarge",
            "ml.c5d.2xlarge",
            "ml.c5d.4xlarge",
            "ml.c5d.9xlarge",
            "ml.c5d.18xlarge",
            "ml.p3.2xlarge",
            "ml.p3.8xlarge",
            "ml.p3.16xlarge",
            "ml.p2.xlarge",
            "ml.p2.8xlarge",
            "ml.p2.16xlarge",
        }
    }

    def clean(self):
        super().clean()

        if self.kind != WorkspaceKindChoices.SAGEMAKER_NOTEBOOK:
            raise ValidationError(
                f"{self.get_kind_display()} is not yet supported"
            )

        if self.instance_type not in self.ALLOWED_INSTANCE_TYPES[self.kind]:
            raise ValidationError(
                f"Instance type for {self.get_kind_display()} must be one of {self.ALLOWED_INSTANCE_TYPES[self.kind]}"
            )


class WorkspaceStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    # Rest from https://github.com/awslabs/service-workbench-on-aws/blob/e800cea5f30aa2208e11962207f6c2e181ddbde6/addons/addon-base-raas/packages/base-raas-services/lib/environment/service-catalog/environent-sc-status-enum.js#L16
    PENDING = "PENDING", "Pending"
    TAINTED = "TAINTED", "Tainted"
    FAILED = "FAILED", "Failed"
    COMPLETED = "COMPLETED", "Available"
    STARTING = "STARTING", "Starting"
    STARTING_FAILED = "STARTING_FAILED", "Starting Failed"
    STOPPED = "STOPPED", "Stopped"
    STOPPING = "STOPPING", "Stopping"
    STOPPING_FAILED = "STOPPING_FAILED", "Stopping Failed"
    TERMINATING = "TERMINATING", "Terminating"
    TERMINATED = "TERMINATED", "Terminated"
    TERMINATING_FAILED = "TERMINATING_FAILED", "Terminating Failed"


class Workspace(UUIDModel):
    service_workbench_id = models.UUIDField(
        editable=False, null=True, default=None
    )
    user = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    phase = models.ForeignKey(Phase, on_delete=models.PROTECT)
    configuration = models.ForeignKey(
        WorkspaceTypeConfiguration, on_delete=models.PROTECT
    )
    allowed_ip = models.GenericIPAddressField()

    # The notebook urls are 3000+ chars, so use a text field
    notebook_url = models.TextField(blank=True, editable=False)

    status = models.CharField(
        max_length=18,
        choices=WorkspaceStatus.choices,
        default=WorkspaceStatus.QUEUED,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            on_commit(
                lambda: celery_app.signature(
                    "grandchallenge.workspaces.tasks.create_workspace"
                ).apply_async(kwargs={"workspace_pk": self.pk})
            )
            assign_perm("view_workspace", self.user, self)

    @property
    def animate(self):
        return self.status in {
            WorkspaceStatus.PENDING,
            WorkspaceStatus.STARTING,
            WorkspaceStatus.STOPPING,
            WorkspaceStatus.TERMINATING,
        }

    @property
    def can_terminate(self):
        return self.status in {
            WorkspaceStatus.TAINTED,
            WorkspaceStatus.FAILED,
            WorkspaceStatus.COMPLETED,
            WorkspaceStatus.STARTING,
            WorkspaceStatus.STARTING_FAILED,
            WorkspaceStatus.STOPPED,
            WorkspaceStatus.STOPPING_FAILED,
            WorkspaceStatus.STOPPING,
            WorkspaceStatus.TERMINATING_FAILED,
        }

    @property
    def can_connect(self):
        return (
            self.status
            in {
                WorkspaceStatus.TAINTED,
                WorkspaceStatus.COMPLETED,
                WorkspaceStatus.TERMINATING_FAILED,
            }
            and self.notebook_url
        )

    @property
    def can_stop(self):
        return self.status in {WorkspaceStatus.COMPLETED}

    @property
    def can_start(self):
        return self.status in {WorkspaceStatus.STOPPED}

    @property
    def status_context(self):
        if self.status == WorkspaceStatus.COMPLETED:
            return "success"
        elif self.status in {
            WorkspaceStatus.PENDING,
            WorkspaceStatus.STOPPED,
            WorkspaceStatus.STOPPING,
            WorkspaceStatus.STARTING,
            WorkspaceStatus.TAINTED,
        }:
            return "warning"
        elif self.status in {
            WorkspaceStatus.FAILED,
            WorkspaceStatus.TERMINATING,
            WorkspaceStatus.TERMINATING_FAILED,
        }:
            return "danger"
        elif self.status in {WorkspaceStatus.QUEUED}:
            return "info"
        else:
            return "secondary"

    def get_absolute_url(self):
        return reverse(
            "workspaces:detail",
            kwargs={
                "challenge_short_name": self.phase.challenge.short_name,
                "pk": self.pk,
            },
        )
