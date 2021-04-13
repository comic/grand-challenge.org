import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from grandchallenge.evaluation.models import Phase
from grandchallenge.workspaces.crypters import FernetCrypter


class ProviderChoices(models.IntegerChoices):
    INTERNAL = 0, "internal"  # Lower case as this is the provider id


class Token(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    email = models.EmailField()
    _token = models.TextField(db_column="token")
    provider = models.PositiveSmallIntegerField(
        choices=ProviderChoices.choices, default=ProviderChoices.INTERNAL
    )

    def __str__(self):
        return f"{self.user}"

    @property
    def token(self):
        if settings.WORKSPACES_SECRET_KEY:
            c = FernetCrypter(secret_key=settings.WORKSPACE_SECRET_KEY)
            return c.decrypt(encoded=self.token)
        else:
            return self._token

    @token.setter
    def token(self, value):
        if settings.WORKSPACES_SECRET_KEY:
            c = FernetCrypter(secret_key=settings.WORKSPACES_SECRET_KEY)
            self._token = c.encrypt(data=value)
        else:
            raise RuntimeError("WORKSPACES_SECRET_KEY is not set")


class WorkspaceKindChoices(models.IntegerChoices):
    SAGEMAKER_NOTEBOOK = 0, "SageMaker Notebook"
    EC2_LINUX = 1, "EC2 Linux"


class WorkspaceType(models.Model):
    name = models.CharField(max_length=32)
    product_id = models.CharField(max_length=32)
    provisioning_artefact_id = models.CharField(max_length=32)
    kind = models.PositiveSmallIntegerField(
        choices=WorkspaceKindChoices.choices
    )

    @property
    def env_type_id(self):
        return f"{self.product_id}-{self.provisioning_artefact_id}"


class WorkspaceTypeConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance_type = models.CharField(max_length=16)
    auto_stop_time = models.PositiveSmallIntegerField(default=10)
    kind = models.PositiveSmallIntegerField(
        choices=WorkspaceKindChoices.choices
    )

    def __str__(self):
        return self.name

    @property
    def name(self):
        return f"{self.instance_type} with {self.auto_stop_time} minute timeout".replace(
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


class PhaseConfiguration(models.Model):
    phase = models.OneToOneField(Phase, on_delete=models.CASCADE)
    allowed_configurations = models.ManyToManyField(
        WorkspaceTypeConfiguration,
        blank=True,
        related_name="phase_configurations",
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


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.SET_NULL
    )
    phase_configuration = models.ForeignKey(
        PhaseConfiguration, on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=18,
        choices=WorkspaceStatus.choices,
        default=WorkspaceStatus.QUEUED,
    )
