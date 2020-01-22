import logging
from datetime import datetime, timedelta
from urllib.parse import unquote, urljoin

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm
from rest_framework.authtoken.models import Token
from simple_history.models import HistoricalRecords

from grandchallenge.challenges.models import get_logo_path
from grandchallenge.container_exec.backends.docker import Service
from grandchallenge.container_exec.models import ContainerImageModel
from grandchallenge.container_exec.tasks import start_service, stop_service
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import public_s3_storage
from grandchallenge.subdomains.utils import reverse

__doc__ = """
Workstations are used to view, annotate and upload images to grand challenge.
A `workstation admin` is able to upload a ``WorkstationImage``, which is a docker container image.
A ``WorkstationImage`` expose a http and, optionally, a websocket port.
A `workstation user` can then launch a workstation ``Session`` for a particular ``WorkstationImage``.

When a new session is started, a new container instance of the selected ``WorkstationImage`` is lauched on the docker host.
The connection to the container will be proxied, and only accessible to the user that created the session.
The proxy will map the http and websocket connections from the user to the running instance, which is mapped by the container hostname.
The container instance will have the users API token set in the environment, so that it is able to interact with the grand challenge API as this user.
The user is able to stop the container, otherwise it will be terminated after ``maxmium_duration`` is reached.
"""

logger = logging.getLogger(__name__)


class Workstation(UUIDModel, TitleSlugDescriptionModel):
    """Store the title and description of a workstation."""

    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage
    )
    editors_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="editors_of_workstation",
    )
    users_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="users_of_workstation",
    )
    config = models.ForeignKey(
        "workstation_configs.WorkstationConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        ordering = ("created", "title")

    @property
    def latest_ready_image(self):
        """
        Returns
        -------
            The most recent container image for this workstation
        """
        return (
            self.workstationimage_set.filter(ready=True)
            .order_by("-created")
            .first()
        )

    def __str__(self):
        return f"Workstation {self.title}"

    def get_absolute_url(self):
        return reverse("workstations:detail", kwargs={"slug": self.slug})

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.users_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_users"
        )

    def assign_permissions(self):
        # Allow the editors and users groups to view this workstation
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"view_{self._meta.model_name}", self.users_group, self)
        # Allow the editors to change this workstation
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def is_editor(self, user):
        return user.groups.filter(pk=self.editors_group.pk).exists()

    def add_editor(self, user):
        return user.groups.add(self.editors_group)

    def remove_editor(self, user):
        return user.groups.remove(self.editors_group)

    def is_user(self, user):
        return user.groups.filter(pk=self.users_group.pk).exists()

    def add_user(self, user):
        return user.groups.add(self.users_group)

    def remove_user(self, user):
        return user.groups.remove(self.users_group)


@receiver(post_delete, sender=Workstation)
def delete_workstation_groups_hook(*_, instance: Workstation, using, **__):
    """
    Deletes the related groups.

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    try:
        instance.editors_group.delete(using=using)
    except ObjectDoesNotExist:
        pass

    try:
        instance.users_group.delete(using=using)
    except ObjectDoesNotExist:
        pass


class WorkstationImage(UUIDModel, ContainerImageModel):
    """
    A ``WorkstationImage`` is a docker container image of a workstation.

    Parameters
    ----------
    workstation
        A ``Workstation`` can have multiple ``WorkstationImage``, that
        represent different versions of a workstation
    http_port
        This container will expose a http server on this port
    websocket_port
        This container will expose a websocket on this port. Any relative url
        that starts with ``/mlab4d4c4142`` will be proxied to this port.
    initial_path
        The initial path that users will navigate to in order to load the
        workstation
    """

    workstation = models.ForeignKey(Workstation, on_delete=models.CASCADE)
    http_port = models.PositiveIntegerField(
        default=8080, validators=[MaxValueValidator(2 ** 16 - 1)]
    )
    websocket_port = models.PositiveIntegerField(
        default=4114, validators=[MaxValueValidator(2 ** 16 - 1)]
    )
    initial_path = models.CharField(
        max_length=256,
        default="cirrus",
        validators=[
            RegexValidator(
                regex=r"^(?:[^/][^\s]*)\Z",
                message="This path is invalid, it must not start with a /",
            )
        ],
    )

    class Meta(UUIDModel.Meta, ContainerImageModel.Meta):
        ordering = ("created", "creator")

    def __str__(self):
        return f"Workstation Image {self.pk}"

    def get_absolute_url(self):
        return reverse(
            "workstations:image-detail",
            kwargs={"slug": self.workstation.slug, "pk": self.pk},
        )

    def assign_permissions(self):
        # Allow the editors group to view this workstation image
        assign_perm(
            f"view_{self._meta.model_name}",
            self.workstation.editors_group,
            self,
        )
        # Allow the editors to change this workstation image
        assign_perm(
            f"change_{self._meta.model_name}",
            self.workstation.editors_group,
            self,
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()


class Session(UUIDModel):
    """
    Tracks who has launched workstation images. The ``WorkstationImage`` will
    be launched as a ``Service``. The ``Session`` is responsible for starting
    and stopping the ``Service``.

    Parameters
    ----------
    status
        Stores what has happened with the service, is it running, errored, etc?
    creator
        Who created the session? This is also the only user that should be able
        to access the launched service.
    workstation_image
        The container image that will be launched by this ``Session``.
    maximum_duration
        The maximum time that the service can be active before it is terminated
    user_finished
        Indicates if the user has chosen to end the session early
    history
        The history of this Session
    """

    QUEUED = 0
    STARTED = 1
    RUNNING = 2
    FAILED = 3
    STOPPED = 4

    # These should match the values in session.js
    STATUS_CHOICES = (
        (QUEUED, "Queued"),
        (STARTED, "Started"),
        (RUNNING, "Running"),
        (FAILED, "Failed"),
        (STOPPED, "Stopped"),
    )

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=QUEUED
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    workstation_image = models.ForeignKey(
        WorkstationImage, on_delete=models.CASCADE
    )
    maximum_duration = models.DurationField(default=timedelta(minutes=10))
    user_finished = models.BooleanField(default=False)
    logs = models.TextField(editable=False, blank=True)
    history = HistoricalRecords(excluded_fields=["logs"])

    class Meta(UUIDModel.Meta):
        ordering = ("created", "creator")

    def __str__(self):
        return f"Session {self.pk}"

    @property
    def task_kwargs(self) -> dict:
        """
        Returns
        -------
            The kwargs that need to be passed to celery to get this object
        """
        return {
            "app_label": self._meta.app_label,
            "model_name": self._meta.model_name,
            "pk": self.pk,
        }

    @property
    def hostname(self) -> str:
        """
        Returns
        -------
            The unique hostname for this session
        """
        return (
            f"{self.pk}.{self._meta.model_name}.{self._meta.app_label}".lower()
        )

    @property
    def expires_at(self) -> datetime:
        """
        Returns
        -------
            The time when this session expires.
        """
        return self.created + self.maximum_duration

    @property
    def environment(self) -> dict:
        """
        Returns
        -------
            The environment variables that should be set on the container.
        """
        env = {"GRAND_CHALLENGE_API_ROOT": unquote(reverse("api:api-root"))}

        if self.creator:
            env.update(
                {
                    "GRAND_CHALLENGE_AUTHORIZATION": f"TOKEN {Token.objects.get_or_create(user=self.creator)[0].key}"
                }
            )

        if settings.DEBUG:
            # Allow the container to communicate with the dev environment
            env.update({"GRAND_CHALLENGE_UNSAFE": "true"})

        return env

    @property
    def service(self) -> Service:
        """
        Returns
        -------
            The service for this session, could be active or inactive.
        """
        return Service(
            job_id=self.pk,
            job_model=f"{self._meta.app_label}-{self._meta.model_name}",
            exec_image=self.workstation_image.image,
            exec_image_sha256=self.workstation_image.image_sha256,
        )

    @property
    def workstation_url(self) -> str:
        """
        Returns
        -------
            The url that users will use to access the workstation instance.
        """
        return urljoin(
            self.get_absolute_url(), self.workstation_image.initial_path
        )

    def start(self) -> None:
        """
        Starts the service for this session, ensuring that the
        ``workstation_image`` is ready to be used and that
        ``WORKSTATIONS_MAXIMUM_SESSIONS`` has not been reached.

        Raises
        ------
        RunTimeError
            If the service cannot be started.
        """
        try:
            if not self.workstation_image.ready:
                raise RuntimeError("Workstation image was not ready")

            if (
                Session.objects.all()
                .filter(status__in=[Session.RUNNING, Session.STARTED])
                .count()
                >= settings.WORKSTATIONS_MAXIMUM_SESSIONS
            ):
                raise RuntimeError("Too many sessions are running")

            self.service.start(
                http_port=self.workstation_image.http_port,
                websocket_port=self.workstation_image.websocket_port,
                hostname=self.hostname,
                environment=self.environment,
            )
            self.update_status(status=self.STARTED)
        except RuntimeError:
            self.update_status(status=self.FAILED)

    def stop(self) -> None:
        """Stop the service for this session, cleaning up all of the containers."""
        self.logs = self.service.logs()
        self.service.stop_and_cleanup()
        self.update_status(status=self.STOPPED)

    def update_status(self, *, status: STATUS_CHOICES) -> None:
        """
        Updates the status of this session.

        Parameters
        ----------
        status
            The new status for this session.
        """
        self.status = status
        self.save()

    def get_absolute_url(self):
        return reverse(
            "workstations:session-detail",
            kwargs={
                "slug": self.workstation_image.workstation.slug,
                "pk": self.pk,
            },
        )

    def assign_permissions(self):
        # Allow the editors group to view and change this session
        assign_perm(
            f"view_{self._meta.model_name}",
            self.workstation_image.workstation.editors_group,
            self,
        )
        assign_perm(
            f"change_{self._meta.model_name}",
            self.workstation_image.workstation.editors_group,
            self,
        )
        # Allow the session creator to view or change this
        assign_perm(f"view_{self._meta.model_name}", self.creator, self)
        assign_perm(f"change_{self._meta.model_name}", self.creator, self)

    def save(self, *args, **kwargs) -> None:
        """Save the session instance, starting or stopping the service if needed."""
        created = self._state.adding

        super().save(*args, **kwargs)

        if created:
            self.assign_permissions()
            start_service.apply_async(kwargs=self.task_kwargs)
        elif self.user_finished and self.status != self.STOPPED:
            stop_service.apply_async(kwargs=self.task_kwargs)
