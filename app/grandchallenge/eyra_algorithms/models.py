import logging

from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel
from grandchallenge.eyra_data.models import DataType, DataFile
from grandchallenge.eyra_algorithms.validators import IdExistsInDockerRegistryValidator

logger = logging.getLogger(__name__)


class Interface(UUIDModel):
    created = models.DateTimeField(auto_now_add=True, help_text="Moment of creation")
    name = models.CharField(max_length=64, unique=True)
    output_type = models.ForeignKey(
        DataType,
        on_delete = models.CASCADE,
        related_name='+',
    )

    def __str__(self):
        return self.name


class Input(UUIDModel):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=64, unique=True)
    interface = models.ForeignKey(Interface, on_delete=models.CASCADE, related_name='inputs')
    type = models.ForeignKey(
        DataType,
        on_delete = models.CASCADE,
        related_name='+',
    )

    def __str__(self):
        return self.name


class Algorithm(UUIDModel):
    """
    An Algorithm represents a group (different versions) of (benchmark solving) implementations.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="algorithms",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this solution in markdown.",
    )
    interface = models.ForeignKey(Interface, on_delete=models.CASCADE, related_name='algorithms')

    def __str__(self):
        return self.name


class Implementation(UUIDModel):
    """
    An implementation represents a (container) that implements an interface (produces
    specific output type from specific input types).
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="implementations",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this implementation in markdown.",
    )
    container = models.CharField(max_length=64, unique=True, validators=[IdExistsInDockerRegistryValidator])
    command = models.CharField(max_length=255, blank=True, null=True)
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE, blank=True, null=True, related_name='implementations')
    version = models.CharField(
        max_length=64,
        help_text="The Algorithm version",
        blank=True,
        null=True,
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
    implementation = models.ForeignKey(Implementation, on_delete=models.CASCADE)
    output = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='output_of_job', null=False, blank=False)

    def delete(self, using=None, keep_parents=False):
        if self.output:
            self.output.delete()
        super().delete(using, keep_parents)

    def input_name_data_file_pk_map(self):
        return {job_input.input.name: job_input.data_file.pk for job_input in self.inputs.all()}


class JobInput(UUIDModel):
    input = models.ForeignKey(Input, on_delete=models.CASCADE, related_name='+')
    data_file = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='job_inputs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='inputs')
