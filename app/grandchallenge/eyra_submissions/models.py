import logging

from django.conf import settings
from django.db import models

from grandchallenge.cases.models import RawImageUploadSession, RawImageFile
from grandchallenge.container_exec.models import (
    ContainerExecJobModel,
    ContainerImageModel,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.eyra_benchmarks.models import Benchmark
from grandchallenge.jqfileupload.models import StagedFile

logger = logging.getLogger(__name__)


def get_output_filename(obj, filename):
    return 'job_output/'+str(obj.id)


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
    output = models.FileField(blank=True, null=True, upload_to=get_output_filename)


# An algorithm submission
class Submission(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=32, unique=True, null=True)
    description_html = models.TextField(blank=True)
    benchmark = models.ForeignKey(Benchmark, on_delete=models.CASCADE)
    algorithm_job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, related_name='_submission_algorithm')
    evaluation_job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, related_name='_evaluation_algorithm')


