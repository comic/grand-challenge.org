from decimal import Decimal
from typing import Tuple, Type

from django.conf import settings
from django.core.files import File
from django.db import models
from django.db.models import Avg, F
from django.utils.text import get_valid_filename
from django.utils.timezone import now

from grandchallenge.components.backends.docker import Executor
from grandchallenge.components.tasks import execute_job
from grandchallenge.core.storage import private_s3_storage
from grandchallenge.core.validators import ExtensionValidator


class ComponentQuerySet(models.QuerySet):
    def with_duration(self):
        """Annotate the queryset with the duration of completed jobs"""
        return self.annotate(duration=F("completed_at") - F("started_at"))

    def average_duration(self):
        """Calculate the average duration that completed jobs ran for"""
        return (
            self.with_duration()
            .exclude(duration=None)
            .aggregate(Avg("duration"))["duration__avg"]
        )


class ComponentJob(models.Model):
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
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)

    objects = ComponentQuerySet.as_manager()

    def update_status(self, *, status: STATUS_CHOICES, output: str = ""):
        self.status = status

        if output:
            self.output = output

        if status == self.STARTED and self.started_at is None:
            self.started_at = now()
        elif (
            status in [self.SUCCESS, self.FAILURE, self.CANCELLED]
            and self.completed_at is None
        ):
            self.completed_at = now()

        self.save()

    @property
    def container(self) -> "ComponentImage":
        """
        Returns the container object associated with this instance, which
        should be a foreign key to an object that is a subclass of
        ComponentImage
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
        Return the executor class for this job.

        The executor class must be a subclass of ``Executor``.
        """
        raise NotImplementedError

    def create_result(self, *, result: dict):
        """
        The result object for this job must be created here..

        Called once the container has finished its execution.
        """
        raise NotImplementedError

    def schedule_job(self):

        kwargs = {}

        if self.container.requires_gpu:
            kwargs.update({"queue": "gpu"})

        if getattr(self.container, "queue_override", None):
            kwargs.update({"queue": self.container.queue_override})

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
        f"{get_valid_filename(filename)}"
    )


class ComponentImage(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    staged_image_uuid = models.UUIDField(blank=True, null=True, editable=False)
    image = models.FileField(
        blank=True,
        upload_to=docker_image_path,
        validators=[
            ExtensionValidator(allowed_extensions=(".tar", ".tar.gz"))
        ],
        help_text=(
            ".tar.gz archive of the container image produced from the command "
            "'docker save IMAGE | gzip -c > IMAGE.tar.gz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
        storage=private_s3_storage,
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
