import uuid
from typing import Tuple, Type

from django.conf import settings
from django.core.files import File
from django.db import models
from social_django.fields import JSONField

from grandchallenge.evaluation.backends.dockermachine.evaluator import \
    Evaluator
from grandchallenge.evaluation.validators import ExtensionValidator


class UUIDModel(models.Model):
    """
    Abstract class that consists of a UUID primary key, created and modified
    times
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CeleryJobModel(models.Model):
    # The job statuses come directly from celery.result.AsyncResult.status:
    # http://docs.celeryproject.org/en/latest/reference/celery.result.html
    PENDING = 0
    STARTED = 1
    RETRY = 2
    FAILURE = 3
    SUCCESS = 4
    CANCELLED = 5

    STATUS_CHOICES = (
        (PENDING, 'The task is waiting for execution'),
        (STARTED, 'The task has been started'),
        (RETRY, 'The task is to be retried, possibly because of failure'),
        (
            FAILURE,
            'The task raised an exception, or has exceeded the retry limit',
        ),
        (SUCCESS, 'The task executed successfully'),
        (CANCELLED, 'The task was cancelled'),
    )

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING
    )
    status_history = JSONField(default=dict)
    output = models.TextField()

    def update_status(self, *, status: STATUS_CHOICES, output: str = None):
        self.status = status

        if output:
            self.output = output

        self.save()

    @property
    def container(self) -> 'DockerImageModel':
        """
        Returns the container object associated with this instance, which
        should be a foreign key to an object that is a subclass of
        DockerImageModel
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
    def evaluator_cls(self) -> Type[Evaluator]:
        """
        Returns the evaluator class for this job, which must be a subclass of
        Evaluator
        """
        raise NotImplementedError

    class Meta:
        abstract = True


def docker_image_path(instance, filename):
    return (
        f'docker/'
        f'images/'
        f'{instance._meta.app_label.lower()}/'
        f'{instance._meta.model_name.lower()}/'
        f'{instance.pk}/'
        f'{filename}'
    )


class DockerImageModel(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    image = models.FileField(
        upload_to=docker_image_path,
        validators=[ExtensionValidator(allowed_extensions=('.tar',))],
        help_text=(
            'Tar archive of the container image produced from the command '
            '`docker save IMAGE > IMAGE.tar`. See '
            'https://docs.docker.com/engine/reference/commandline/save/'
        ),
    )
    image_sha256 = models.CharField(editable=False, max_length=71)
    ready = models.BooleanField(
        default=False,
        editable=False,
        help_text="Is this image ready to be used?",
    )
    status = models.TextField(editable=False)

    class Meta:
        abstract = True
