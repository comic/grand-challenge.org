from decimal import Decimal
from typing import Tuple, Type

from django.conf import settings
from django.core.files import File
from django.db import models

from grandchallenge.container_exec.backends.docker import Executor
from grandchallenge.container_exec.tasks import execute_job
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.jqfileupload.models import StagedFile


class ContainerExecJobModel(models.Model):
    # The job statuses come directly from celery.result.AsyncResult.status:
    # http://docs.celeryproject.org/en/latest/reference/celery.result.html
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

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING
    )
    output = models.TextField()

    def update_status(self, *, status: STATUS_CHOICES, output: str = None):
        self.status = status

        if output:
            self.output = output

        self.save()

    @property
    def container(self) -> "ContainerImageModel":
        """
        Returns the container object associated with this instance, which
        should be a foreign key to an object that is a subclass of
        ContainerImageModel
        """
        raise NotImplementedError

    @property
    def input_files(self) -> Tuple[File, ...]:
        """
        Returns a tuple of the input files that will be mounted into the
        container when it is executed
        """
        raise NotImplementedError

    @property
    def executor_cls(self) -> Type[Executor]:
        """
        Returns the executor class for this job, which must be a subclass of
        Executor
        """
        raise NotImplementedError

    def create_result(self, *, result: dict):
        """
        This is called at the end of the container execution, the result object
        for this job must be created by this function.
        """
        raise NotImplementedError

    def schedule_job(self):

        kwargs = {"task_id": str(self.pk)}

        if self.container.requires_gpu:
            kwargs.update({"queue": "gpu"})

        execute_job.apply_async(
            **kwargs,
            kwargs={
                "job_pk": self.pk,
                "job_app_label": self._meta.app_label,
                "job_model_name": self._meta.model_name,
            },
        )

    class Meta:
        abstract = True


def docker_image_path(instance, filename):
    return (
        f"docker/"
        f"images/"
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{instance.pk}/"
        f"{filename}"
    )


class ContainerImageModel(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    staged_image_uuid = models.UUIDField(blank=True, null=True, editable=False)
    image = models.FileField(
        blank=True,
        upload_to=docker_image_path,
        validators=[ExtensionValidator(allowed_extensions=(".tar",))],
        help_text=(
            "Tar archive of the container image produced from the command "
            "`docker save IMAGE > IMAGE.tar`. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
    )

    image_sha256 = models.CharField(editable=False, max_length=71)

    ready = models.BooleanField(
        default=False,
        editable=False,
        help_text="Is this image ready to be used?",
    )
    status = models.TextField(editable=False)

    requires_gpu = models.BooleanField(default=False)
    requires_gpu_memory_gb = models.PositiveIntegerField(default=4)
    requires_memory_gb = models.PositiveIntegerField(default=4)
    # Support up to 99.99 cpu cores
    requires_cpu_cores = models.DecimalField(
        default=Decimal("1.0"), max_digits=4, decimal_places=2
    )

    class Meta:
        abstract = True
