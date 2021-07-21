import json
import logging
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Avg, F, QuerySet
from django.db.transaction import on_commit
from django.utils.functional import cached_property
from django.utils.text import get_valid_filename
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_extensions.db.fields import AutoSlugField

from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.components.tasks import execute_job, validate_docker_image
from grandchallenge.components.validators import validate_safe_path
from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
)
from grandchallenge.core.validators import (
    ExtensionValidator,
    MimeTypeValidator,
)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_INTERFACE_SLUG = "generic-overlay"


class InterfaceKindChoices(models.TextChoices):
    """Interface kind choices."""

    STRING = "STR", _("String")
    INTEGER = "INT", _("Integer")
    FLOAT = "FLT", _("Float")
    BOOL = "BOOL", _("Bool")

    # Annotation Types
    TWO_D_BOUNDING_BOX = "2DBB", _("2D bounding box")
    MULTIPLE_TWO_D_BOUNDING_BOXES = "M2DB", _("Multiple 2D bounding boxes")
    DISTANCE_MEASUREMENT = "DIST", _("Distance measurement")
    MULTIPLE_DISTANCE_MEASUREMENTS = (
        "MDIS",
        _("Multiple distance measurements"),
    )
    POINT = "POIN", _("Point")
    MULTIPLE_POINTS = "MPOI", _("Multiple points")
    POLYGON = "POLY", _("Polygon")
    MULTIPLE_POLYGONS = "MPOL", _("Multiple polygons")

    # Choice Types
    CHOICE = "CHOI", _("Choice")
    MULTIPLE_CHOICE = "MCHO", _("Multiple choice")

    # Image types
    IMAGE = "IMG", _("Image")
    SEGMENTATION = "SEG", _("Segmentation")
    HEAT_MAP = "HMAP", _("Heat Map")

    # Legacy support
    JSON = "JSON", _("JSON file")
    CSV = "CSV", _("CSV file")
    ZIP = "ZIP", _("ZIP file")


class InterfaceSuperKindChoices(models.TextChoices):
    IMAGE = "I", "Image"
    FILE = "F", "File"
    VALUE = "V", "Value"


class InterfaceKind:
    """Interface kind."""

    InterfaceKindChoices = InterfaceKindChoices

    @staticmethod
    def interface_type_file():
        """Interface kinds that are files:

        * CSV file
        * JSON file
        * ZIP file
        """
        return (
            InterfaceKind.InterfaceKindChoices.CSV,
            InterfaceKind.InterfaceKindChoices.JSON,
            InterfaceKind.InterfaceKindChoices.ZIP,
        )

    @staticmethod
    def interface_type_image():
        """Interface kinds that are images:

        * Image
        * Heat Map
        * Segmentation
        """
        return (
            InterfaceKind.InterfaceKindChoices.IMAGE,
            InterfaceKind.InterfaceKindChoices.HEAT_MAP,
            InterfaceKind.InterfaceKindChoices.SEGMENTATION,
        )

    @staticmethod
    def interface_type_annotation():
        """Interface kinds that are annotations:


        * 2D bounding box
        * Multiple 2D bounding boxes
        * Distance measurement
        * Multiple distance measurements
        * Point
        * Multiple points
        * Polygon
        * Multiple polygons

        Example json for 2D bounding box annotation

        .. code-block:: json

            {
                "type": "2D bounding box",
                "corners": [
                    [ 130.80001831054688, 148.86666870117188, 0.5009999871253967],
                    [ 69.73332977294922, 148.86666870117188, 0.5009999871253967],
                    [ 69.73332977294922, 73.13333129882812, 0.5009999871253967 ],
                    [ 130.80001831054688, 73.13333129882812, 0.5009999871253967]
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple 2D bounding boxes annotation

        .. code-block:: json

            {
                "type": "Multiple 2D bounding boxes",
                "boxes": [
                    {
                    "corners": [
                        [ 92.66666412353516, 136.06668090820312, 0.5009999871253967],
                        [ 54.79999923706055, 136.06668090820312, 0.5009999871253967],
                        [ 54.79999923706055, 95.53333282470703, 0.5009999871253967],
                        [ 92.66666412353516, 95.53333282470703, 0.5009999871253967]
                    ]},
                    {
                    "corners": [
                        [ 92.66666412353516, 136.06668090820312, 0.5009999871253967],
                        [ 54.79999923706055, 136.06668090820312, 0.5009999871253967],
                        [ 54.79999923706055, 95.53333282470703, 0.5009999871253967],
                        [ 92.66666412353516, 95.53333282470703, 0.5009999871253967]
                    ]}
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Distance measurement annotation

        .. code-block:: json

            {
                "type": "Distance measurement",
                "start": [ 59.79176712036133, 78.76753997802734, 0.5009999871253967 ],
                "end": [ 69.38014221191406, 143.75546264648438, 0.5009999871253967 ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple distance measurement annotation

        .. code-block:: json

            {
                "type": "Multiple distance measurements",
                "lines": [
                    {
                        "start": [ 49.733333587646484, 103.26667022705078, 0.5009999871253967 ],
                        "end": [ 55.06666564941406, 139.26666259765625, 0.5009999871253967 ]
                    },
                    {
                        "start": [ 49.733333587646484, 103.26667022705078, 0.5009999871253967 ],
                        "end": [ 55.06666564941406, 139.26666259765625, 0.5009999871253967 ]
                    }
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Point annotation

        .. code-block:: json

            {
                "point": [ 152.13333129882812, 111.0, 0.5009999871253967 ],
                "type": "Point",
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple points annotation

        .. code-block:: json

            {
                "type": "Multiple points",
                "points": [
                    {
                        "point": [
                            96.0145263671875, 79.83292388916016, 0.5009999871253967
                        ],
                    },
                    {
                        "point": [
                            130.10653686523438, 115.52300262451172, 0.5009999871253967
                        ],
                    }
                ],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Polygon annotation

        .. code-block:: json

            {
                "type": "Polygon",
                "seed_point": [ 76.413756408691, 124.014717102050, 0.5009999871253967 ],
                "path_points": [
                    [ 76.41375842260106, 124.01471710205078, 0.5009999871253967 ],
                    [ 76.41694876387268, 124.0511828696491, 0.5009999871253967 ],
                    [ 76.42642285078242, 124.0865406433515, 0.5009999871253967 ]
                ],
                "sub_type": "brush",
                "groups": [],
                "version": { "major": 1, "minor": 0 }
            }

        Example json for Multiple polygon annotation

        .. code-block:: json

            {
                "type": "Multiple polygons",
                "polygons": [
                    {
                        "seed_point": [ 55.82666793823242, 90.46666717529297, 0.5009999871253967 ],
                        "path_points": [
                            [ 55.82667599387105, 90.46666717529297, 0.5009999871253967 ],
                            [ 55.93921357544119, 90.88666314747366, 0.5009999871253967 ],
                            [ 56.246671966051736, 91.1941215380842, 0.5009999871253967 ],
                            [ 56.66666793823242, 91.30665911965434, 0.5009999871253967 ]
                        ],
                        "sub_type": "brush",
                        "groups": [ "manual"],
                    },
                    {
                        "seed_point": [ 90.22666564941406, 96.06666564941406, 0.5009999871253967 ],
                        "path_points": [
                            [ 90.22667370505269, 96.06666564941406, 0.5009999871253967 ],
                            [ 90.33921128662283, 96.48666162159475, 0.5009999871253967 ],
                            [ 90.64666967723338, 96.7941200122053, 0.5009999871253967 ]
                        ],
                        "sub_type": "brush",
                        "groups": []
                    }
                ],
                "version": { "major": 1, "minor": 0 }
            }

        """
        return (
            InterfaceKind.InterfaceKindChoices.TWO_D_BOUNDING_BOX,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
            InterfaceKind.InterfaceKindChoices.DISTANCE_MEASUREMENT,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
            InterfaceKind.InterfaceKindChoices.POINT,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_POINTS,
            InterfaceKind.InterfaceKindChoices.POLYGON,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_POLYGONS,
        )

    @staticmethod
    def interface_type_simple():
        """Simple interface kinds.

        * String
        * Integer
        * Float
        * Bool
        * Choice
        * Multiple choice
        """
        return (
            InterfaceKind.InterfaceKindChoices.STRING,
            InterfaceKind.InterfaceKindChoices.INTEGER,
            InterfaceKind.InterfaceKindChoices.FLOAT,
            InterfaceKind.InterfaceKindChoices.BOOL,
            InterfaceKind.InterfaceKindChoices.CHOICE,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_CHOICE,
        )


class ComponentInterface(models.Model):
    Kind = InterfaceKind.InterfaceKindChoices

    title = models.CharField(
        max_length=255,
        help_text="Human readable name of this input/output field.",
        unique=True,
    )
    slug = AutoSlugField(populate_from="title")
    description = models.TextField(
        blank=True, help_text="Description of this input/output field."
    )
    default_value = models.JSONField(
        blank=True,
        null=True,
        default=None,
        help_text="Default value for this field, only valid for inputs.",
    )
    kind = models.CharField(
        blank=False,
        max_length=4,
        choices=Kind.choices,
        help_text=(
            "What is the type of this interface? Used to validate interface "
            "values and connections between components."
        ),
    )
    relative_path = models.CharField(
        max_length=255,
        help_text=(
            "The path to the entity that implements this interface relative "
            "to the input or output directory."
        ),
        unique=True,
        validators=[validate_safe_path],
    )
    store_in_database = models.BooleanField(
        default=True,
        editable=True,
        help_text=(
            "Should the value be saved in a database field, "
            "only valid for outputs."
        ),
    )

    def __str__(self):
        return f"{self.title} ({self.get_kind_display()})"

    @property
    def is_image_kind(self):
        return self.kind in InterfaceKind.interface_type_image()

    @property
    def super_kind(self):
        if self.save_in_object_store:
            if self.is_image_kind:
                return InterfaceSuperKindChoices.IMAGE
            else:
                return InterfaceSuperKindChoices.FILE
        else:
            return InterfaceSuperKindChoices.VALUE

    @property
    def save_in_object_store(self):
        # CSV and ZIP should always be saved to S3, others are optional
        return (
            self.is_image_kind
            or self.kind
            in (
                InterfaceKind.InterfaceKindChoices.CSV,
                InterfaceKind.InterfaceKindChoices.ZIP,
            )
            or not self.store_in_database
        )

    def create_instance(self, *, image=None, value=None):
        civ = ComponentInterfaceValue.objects.create(interface=self)

        if image:
            civ.image = image
        elif self.save_in_object_store:
            civ.file = ContentFile(
                json.dumps(value).encode("utf-8"),
                name=Path(self.relative_path).name,
            )
        else:
            civ.value = value

        civ.full_clean()
        civ.save()

        return civ

    class Meta:
        ordering = ("pk",)


def component_interface_value_path(instance, filename):
    # Convert the pk to a hex, padded to 4 chars with zeros
    pk_as_padded_hex = f"{instance.pk:04x}"

    return (
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{pk_as_padded_hex[-4:-2]}/{pk_as_padded_hex[-2:]}/{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class ComponentInterfaceValue(models.Model):
    """Encapsulates the value of an interface at a certain point in the graph."""

    id = models.BigAutoField(primary_key=True)
    interface = models.ForeignKey(
        to=ComponentInterface, on_delete=models.PROTECT
    )
    value = models.JSONField(null=True, blank=True, default=None)
    file = models.FileField(
        null=True,
        blank=True,
        upload_to=component_interface_value_path,
        storage=protected_s3_storage,
        validators=[
            ExtensionValidator(allowed_extensions=(".json", ".zip", ".csv")),
            MimeTypeValidator(
                allowed_types=(
                    "application/json",
                    "application/zip",
                    "text/plain",
                )
            ),
        ],
    )
    image = models.ForeignKey(
        to=Image, null=True, blank=True, on_delete=models.PROTECT
    )

    @property
    def title(self):
        if self.value is not None:
            return str(self.value)
        if self.file:
            return self.file.name
        if self.image:
            return self.image.name
        return ""

    @property
    def has_value(self):
        return self.value is not None or self.image or self.file

    @property
    def decompress(self):
        """
        Should the CIV be decompressed?

        This is only for legacy support of zip file submission for
        prediction evaluation. We should not support this anywhere
        else as it clobbers the input directory.
        """
        return self.interface.kind == InterfaceKindChoices.ZIP

    @cached_property
    def image_file(self):
        """The single image file for this interface"""
        return (
            self.image.files.filter(
                image_type__in=[
                    ImageFile.IMAGE_TYPE_MHD,
                    ImageFile.IMAGE_TYPE_TIFF,
                ]
            )
            .get()
            .file
        )

    @property
    def input_file(self):
        """The file to use as component input"""
        if self.image:
            return self.image_file
        elif self.file:
            return self.file
        else:
            src = NamedTemporaryFile(delete=True)
            src.write(bytes(json.dumps(self.value), "utf-8"))
            src.flush()
            return File(src, name=self.relative_path.name)

    @property
    def relative_path(self):
        """
        Where should the file be located?

        Images need special handling as their names are fixed.
        """
        path = Path(self.interface.relative_path)

        if self.image:
            path /= Path(self.image_file.name).name

        return path

    def __str__(self):
        return f"Component Interface Value {self.pk} for {self.interface}"

    class Meta:
        ordering = ("pk",)


class DurationQuerySet(models.QuerySet):
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
        choices=STATUS_CHOICES, default=PENDING, db_index=True
    )
    stdout = models.TextField()
    stderr = models.TextField(default="")
    error_message = models.CharField(max_length=1024, default="")
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    input_prefixes = models.JSONField(
        default=dict,
        help_text=(
            "Map of the ComponentInterfaceValue id to the path prefix to use "
            "for this input, e.g. {'1': 'foo/bar/'} will place CIV 1 at "
            "/input/foo/bar/<relative_path>",
        ),
    )

    inputs = models.ManyToManyField(
        to=ComponentInterfaceValue,
        related_name="%(app_label)s_%(class)ss_as_input",
    )
    outputs = models.ManyToManyField(
        to=ComponentInterfaceValue,
        related_name="%(app_label)s_%(class)ss_as_output",
    )

    objects = DurationQuerySet.as_manager()

    def update_status(
        self,
        *,
        status: STATUS_CHOICES,
        stdout: str = "",
        stderr: str = "",
        error_message="",
    ):
        self.status = status

        if stdout:
            self.stdout = stdout

        if stderr:
            self.stderr = stderr

        if error_message:
            self.error_message = error_message[:1024]

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
    def output_interfaces(self) -> QuerySet:
        """Returns an unevaluated QuerySet for the output interfaces"""
        raise NotImplementedError

    @property
    def signature(self):
        options = {}

        if self.container.requires_gpu:
            options.update({"queue": "gpu"})

        if getattr(self.container, "queue_override", None):
            options.update({"queue": self.container.queue_override})

        return execute_job.signature(
            kwargs={
                "job_pk": self.pk,
                "job_app_label": self._meta.app_label,
                "job_model_name": self._meta.model_name,
            },
            options=options,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_orig = self.image

    def save(self, *args, **kwargs):
        if self.image != self._image_orig:
            self.ready = False

        super().save(*args, **kwargs)

        if not self.ready:
            on_commit(
                lambda: validate_docker_image.apply_async(
                    kwargs={
                        "app_label": self._meta.app_label,
                        "model_name": self._meta.model_name,
                        "pk": self.pk,
                    }
                )
            )

    class Meta:
        abstract = True
