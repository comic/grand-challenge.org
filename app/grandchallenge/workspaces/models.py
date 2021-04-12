import uuid

from django.contrib.auth import get_user_model
from django.db import models

from grandchallenge.evaluation.models import Phase


class ProviderChoices(models.IntegerChoices):
    INTERNAL = 0, "internal"


class Token(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    token = models.TextField()
    provider = models.PositiveSmallIntegerField(
        choices=ProviderChoices.choices
    )

    def __str__(self):
        return f"{self.user}"


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


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.SET_NULL
    )
    phase_configuration = models.ForeignKey(
        PhaseConfiguration, on_delete=models.CASCADE
    )
