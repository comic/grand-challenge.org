import logging

from django.conf import settings
from django.db import models

from grandchallenge.cases.models import RawImageUploadSession, RawImageFile
from grandchallenge.container_exec.models import (
    ContainerExecJobModel,
    ContainerImageModel,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.eyra_data.models import DataType, DataFile
from grandchallenge.jqfileupload.models import StagedFile

logger = logging.getLogger(__name__)


# An algorithm
class Algorithm(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="algorithms",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=32, unique=True, null=True)
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this algorithm in markdown.",
    )
    output_type = models.ForeignKey(
        DataType,
        on_delete=models.CASCADE,
        related_name='+',
    )
    container = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name


class AlgorithmInput(UUIDModel):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=32, unique=True)
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, related_name='inputs')
    type = models.ForeignKey(
        DataType,
        on_delete = models.CASCADE,
        related_name='+',
    )

    def __str__(self):
        return self.name


class Job(UUIDModel):
    PENDING = 0
    STARTED = 1
    RETRY = 2
    FAILURE = 3
    SUCCESS = 4
    CANCELLED = 5

    STATUS_CHOICES = (
        (PENDING, "Queued"),
        (STARTED, "Started"),
        (RETRY, "Re-Queued"),
        (FAILURE, "Failed"),
        (SUCCESS, "Succeeded"),
        (CANCELLED, "Cancelled"),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING
    )
    started = models.DateTimeField(blank=True, null=True)
    stopped = models.DateTimeField(blank=True, null=True)
    log = models.TextField(blank=True, null=True)
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE)
    output = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='output_of_job', null=True)


class JobInput(UUIDModel):
    algorithm_input = models.ForeignKey(AlgorithmInput, on_delete=models.CASCADE, related_name='jobs')
    data_file = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='job_inputs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='inputs')