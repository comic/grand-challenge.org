import json
import logging
from datetime import datetime, timedelta
from functools import cached_property
from math import ceil
from urllib.parse import unquote, urljoin

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models
from django.db.models.signals import post_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.utils.text import get_valid_filename
from django.utils.timezone import now
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm, remove_perm
from knox.models import AuthToken
from simple_history.models import HistoricalRecords
from stdimage import JPEGField

from grandchallenge.components.backends.docker import Service
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.models import ComponentImage
from grandchallenge.components.tasks import (
    preload_interactive_algorithms,
    start_service,
    stop_service,
)
from grandchallenge.core.models import FieldChangeMixin, UUIDModel
from grandchallenge.core.storage import (
    get_logo_path,
    protected_s3_storage,
    public_s3_storage,
)
from grandchallenge.core.validators import JSONValidator
from grandchallenge.reader_studies.models import (
    InteractiveAlgorithmChoices,
    Question,
    ReaderStudy,
)
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.emails import send_new_feedback_email_to_staff

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

    logo = JPEGField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        variations=settings.STDIMAGE_LOGO_VARIATIONS,
    )
    editors_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="editors_of_workstation",
    )
    users_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="users_of_workstation",
    )
    config = models.ForeignKey(
        "workstation_configs.WorkstationConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    public = models.BooleanField(
        default=False,
        help_text=(
            "If True, all logged in users can use this viewer, "
            "otherwise, only the users group can use this viewer."
        ),
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        ordering = ("created", "title")

    @cached_property
    def active_image(self):
        """
        Returns
        -------
            The desired image version for this workstation or None
        """
        try:
            return (
                self.workstationimage_set.executable_images()
                .filter(is_desired_version=True)
                .get()
            )
        except ObjectDoesNotExist:
            return None

    def __str__(self):
        public = " (Public)" if self.public else ""
        return f"Viewer {self.title}{public}"

    def get_absolute_url(self):
        return reverse("workstations:detail", kwargs={"slug": self.slug})

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.users_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_users"
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()

        super().save(*args, **kwargs)

        self.assign_permissions()

    def assign_permissions(self):
        # Allow the editors and users groups to view this workstation
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"view_{self._meta.model_name}", self.users_group, self)
        # Allow the editors to change this workstation
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )

        g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

        if self.public:
            assign_perm(f"view_{self._meta.model_name}", g_reg, self)
        else:
            remove_perm(f"view_{self._meta.model_name}", g_reg, self)

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


class WorkstationUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Workstation, on_delete=models.CASCADE)


class WorkstationGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Workstation, on_delete=models.CASCADE)


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


class WorkstationImage(UUIDModel, ComponentImage):
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

    SHIM_IMAGE = False

    workstation = models.ForeignKey(Workstation, on_delete=models.PROTECT)
    http_port = models.PositiveIntegerField(
        default=8080, validators=[MaxValueValidator(2**16 - 1)]
    )
    websocket_port = models.PositiveIntegerField(
        default=4114, validators=[MaxValueValidator(2**16 - 1)]
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

    class Meta(UUIDModel.Meta, ComponentImage.Meta):
        ordering = ("created", "creator")

    def get_absolute_url(self):
        return reverse(
            "workstations:image-detail",
            kwargs={"slug": self.workstation.slug, "pk": self.pk},
        )

    @property
    def import_status_url(self) -> str:
        return reverse(
            "workstations:image-import-status-detail",
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

    def get_peer_images(self):
        return WorkstationImage.objects.filter(workstation=self.workstation)


class WorkstationImageUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(
        WorkstationImage, on_delete=models.CASCADE
    )


class WorkstationImageGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(
        WorkstationImage, on_delete=models.CASCADE
    )


ENV_VARS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-06/schema",
    "type": "array",
    "title": "The Environment Variables Schema",
    "description": "Defines environment variable names and values",
    "items": {
        "$id": "#/items",
        "type": "object",
        "title": "The Environment Variable Schema",
        "description": "Defines an environment variable",
        "required": ["name", "value"],
        "additionalProperties": False,
        "properties": {
            "name": {
                "$id": "#/items/properties/name",
                "type": "string",
                "title": "The Name Schema",
                "description": "The name of this environment variable",
                "default": "ENV_VAR",
                "pattern": r"^[A-Z0-9\_]+$",
                "examples": ["ENV_VAR"],
            },
            "value": {
                "$id": "#/items/properties/value",
                "type": "string",
                "title": "The Value Schema",
                "description": "The value of this environment variable",
                "default": "env_var_value",
                "examples": ["env_var_value"],
            },
        },
    },
}


class Session(FieldChangeMixin, UUIDModel):
    """
    Tracks who has launched workstation images. The ``WorkstationImage`` will
    be launched as a ``Service``. The ``Session`` is responsible for starting
    and stopping the ``Service``.

    Parameters
    ----------
    status
        Stores what has happened with the service, is it running, errored, etc?
    region
        Stores which region this session runs in
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

    # These should match the values in workstations/js/session.js
    STATUS_CHOICES = (
        (QUEUED, "Queued"),
        (STARTED, "Started"),
        (RUNNING, "Running"),
        (FAILED, "Failed"),
        (STOPPED, "Stopped"),
    )

    class Region(models.TextChoices):
        # AWS regions
        # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html
        AF_SOUTH_1 = "af-south-1", "Africa (Cape Town)"
        AP_EAST_1 = "ap-east-1", "Asia Pacific (Hong Kong)"
        AP_NORTHEAST_1 = "ap-northeast-1", "Asia Pacific (Tokyo)"
        AP_NORTHEAST_2 = "ap-northeast-2", "Asia Pacific (Seoul)"
        AP_NORTHEAST_3 = "ap-northeast-3", "Asia Pacific (Osaka-Local)"
        AP_SOUTH_1 = "ap-south-1", "Asia Pacific (Mumbai)"
        AP_SOUTHEAST_1 = "ap-southeast-1", "Asia Pacific (Singapore)"
        AP_SOUTHEAST_2 = "ap-southeast-2", "Asia Pacific (Sydney)"
        CA_CENTRAL_1 = "ca-central-1", "Canada (Central)"
        EU_CENTRAL_1 = "eu-central-1", "Europe (Frankfurt)"
        EU_NORTH_1 = "eu-north-1", "Europe (Stockholm)"
        EU_SOUTH_1 = "eu-south-1", "Europe (Milan)"
        EU_WEST_1 = "eu-west-1", "Europe (Ireland)"
        EU_WEST_2 = "eu-west-2", "Europe (London)"
        EU_WEST_3 = "eu-west-3", "Europe (Paris)"
        ME_SOUTH_1 = "me-south-1", "Middle East (Bahrain)"
        SA_EAST_1 = "sa-east-1", "South America (São Paulo)"
        US_EAST_1 = "us-east-1", "US East (N. Virginia)"
        US_EAST_2 = "us-east-2", "US East (Ohio)"
        US_WEST_1 = "us-west-1", "US West (N. California)"
        US_WEST_2 = "us-west-2", "US West (Oregon)"

        # User defined regions
        EU_NL_1 = "eu-nl-1", "Netherlands (Nijmegen)"
        EU_NL_2 = "eu-nl-2", "Netherlands (Amsterdam)"

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=QUEUED, db_index=True
    )
    region = models.CharField(
        max_length=14,
        choices=Region.choices,
        default=Region.EU_NL_1,
        help_text="Which region is this session available in?",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    auth_token = models.ForeignKey(
        AuthToken, null=True, on_delete=models.SET_NULL
    )
    workstation_image = models.ForeignKey(
        WorkstationImage, on_delete=models.PROTECT
    )
    maximum_duration = models.DurationField(default=timedelta(minutes=10))
    user_finished = models.BooleanField(default=False)
    logs = models.TextField(editable=False, blank=True)
    ping_times = models.JSONField(null=True, default=None)
    history = HistoricalRecords(
        excluded_fields=["logs", "ping_times", "auth_token"]
    )
    extra_env_vars = models.JSONField(
        default=list,
        blank=True,
        help_text="Extra environment variables to include in this session",
        validators=[JSONValidator(schema=ENV_VARS_SCHEMA)],
    )

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
            f"{self.pk}-{self._meta.model_name}-{self._meta.app_label}".lower()
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
        env = {var["name"]: var["value"] for var in self.extra_env_vars}

        env.update(
            {
                "GRAND_CHALLENGE_API_ROOT": unquote(reverse("api:api-root")),
                "WORKSTATION_SENTRY_DSN": settings.WORKSTATION_SENTRY_DSN,
                "WORKSTATION_SESSION_ID": str(self.pk),
                "CIRRUS_KEEP_ALIVE_METHOD": "old",
                "AWS_DEFAULT_REGION": str(self.region),
                "INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS": json.dumps(
                    settings.INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS
                ),
                "WORKSTATIONS_MAX_CONCURRENT_API_REQUESTS": str(
                    settings.WORKSTATIONS_MAX_CONCURRENT_API_REQUESTS
                ),
            }
        )

        if self.creator:
            if self.auth_token:
                self.auth_token.delete()

            duration_limit = timedelta(
                seconds=settings.WORKSTATIONS_SESSION_DURATION_LIMIT
            ) + timedelta(minutes=settings.WORKSTATIONS_GRACE_MINUTES)
            auth_token, token = AuthToken.objects.create(
                user=self.creator, expiry=duration_limit
            )

            self.auth_token = auth_token
            self.save()

            env.update({"GRAND_CHALLENGE_AUTHORIZATION": f"Bearer {token}"})

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
            job_id=f"{self._meta.app_label}-{self._meta.model_name}-{self.pk}",
            exec_image_repo_tag=self.workstation_image.original_repo_tag,
            memory_limit=settings.COMPONENTS_MEMORY_LIMIT,
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
        ``WORKSTATIONS_MAXIMUM_SESSIONS`` has not been reached in this region.

        Raises
        ------
        ComponentException
            If the service cannot be started.
        """
        try:
            if not self.workstation_image.can_execute:
                raise ComponentException("Workstation image was not ready")

            if (
                Session.objects.all()
                .filter(
                    status__in=[Session.RUNNING, Session.STARTED],
                    region=self.region,
                )
                .count()
                >= settings.WORKSTATIONS_MAXIMUM_SESSIONS
            ):
                raise ComponentException("Too many sessions are running")

            self.service.start(
                http_port=self.workstation_image.http_port,
                websocket_port=self.workstation_image.websocket_port,
                hostname=self.hostname,
                environment=self.environment,
            )
            self.update_status(status=self.STARTED)
        except Exception:
            self.update_status(status=self.FAILED)
            raise

    def stop(self) -> None:
        """Stop the service for this session, cleaning up all of the containers."""
        self.logs = self.service.logs()
        self.service.stop_and_cleanup()
        self.update_status(status=self.STOPPED)

        if self.auth_token:
            self.auth_token.delete()

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
            "session-detail",
            kwargs={
                "slug": self.workstation_image.workstation.slug,
                "pk": self.pk,
                "rendering_subdomain": self.region,
            },
        )

    @property
    def api_url(self) -> str:
        return reverse("api:session-detail", kwargs={"pk": self.pk})

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

        if created and not self.region:
            # Launch in the first active region if no preference set
            self.region = settings.WORKSTATIONS_ACTIVE_REGIONS[0]

        super().save(*args, **kwargs)

        if created:
            self.assign_permissions()
            on_commit(
                start_service.signature(
                    kwargs=self.task_kwargs,
                    queue=f"workstations-{self.region}",
                ).apply_async
            )
        elif self.user_finished and self.status != self.STOPPED:
            on_commit(
                stop_service.signature(
                    kwargs=self.task_kwargs,
                    queue=f"workstations-{self.region}",
                ).apply_async
            )

        if self.has_changed("status") and self.status == self.STOPPED:
            SessionCost.objects.create(
                session=self,
                duration=now() - self.created,
            )

    def handle_reader_study_switching(self, *, reader_study):
        reader_study.workstation_sessions.add(self)

        if reader_study.questions_with_interactive_algorithm.exists():
            on_commit(
                preload_interactive_algorithms.signature(
                    queue=f"workstations-{self.region}"
                ).apply_async
            )


class SessionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Session, on_delete=models.CASCADE)


class SessionGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Session, on_delete=models.CASCADE)


def feedback_screenshot_filepath(instance, filename):
    return (
        f"session-feedback/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class Feedback(UUIDModel):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    screenshot = models.ImageField(
        upload_to=feedback_screenshot_filepath,
        storage=protected_s3_storage,
        blank=True,
    )
    user_comment = models.TextField()
    context = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs) -> None:
        adding = self._state.adding
        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()
            send_new_feedback_email_to_staff(feedback=self)

    def assign_permissions(self):
        assign_perm(
            f"view_{self._meta.model_name}", self.session.creator, self
        )


class FeedbackUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Feedback, on_delete=models.CASCADE)


class FeedbackGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Feedback, on_delete=models.CASCADE)


class SessionCost(UUIDModel):
    session = models.OneToOneField(
        Session,
        related_name="session_cost",
        null=True,
        on_delete=models.SET_NULL,
    )
    duration = models.DurationField()
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    reader_studies = models.ManyToManyField(
        to=ReaderStudy,
        through="SessionCostReaderStudy",
        related_name="session_costs",
        blank=True,
        help_text="Reader studies accessed during session",
    )
    interactive_algorithms = models.JSONField(
        blank=True,
        default=list,
        help_text=(
            "The interactive algorithms for which hardware has been initialized during the session."
        ),
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "enum": InteractiveAlgorithmChoices.values,
                        "type": "string",
                    },
                    "uniqueItems": True,
                }
            )
        ],
    )

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            self.creator = self.session.creator
            reader_studies = self.session.reader_studies.all()
            self.reader_studies.set(reader_studies)
            self.interactive_algorithms = list(
                Question.objects.filter(reader_study__in=reader_studies)
                .exclude(interactive_algorithm="")
                .values_list("interactive_algorithm", flat=True)
                .order_by()
                .distinct()
            )

        super().save(*args, **kwargs)

    @property
    def credits_per_hour(self):
        if self.interactive_algorithms:
            return 1000
        else:
            return 500

    @property
    def credits_consumed(self):
        return ceil(
            self.duration.total_seconds() / 3600 * self.credits_per_hour
        )


class SessionCostReaderStudy(models.Model):
    session_cost = models.ForeignKey(SessionCost, on_delete=models.CASCADE)
    reader_study = models.ForeignKey(ReaderStudy, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session_cost", "reader_study"],
                name="unique_session_cost_reader_study",
            )
        ]
