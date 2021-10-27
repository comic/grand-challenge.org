import json
import logging
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from celery import signature
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Avg, F, QuerySet
from django.db.transaction import on_commit
from django.forms import ModelChoiceField, ModelMultipleChoiceField
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.utils.text import get_valid_filename
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_extensions.db.fields import AutoSlugField

from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.components.tasks import (
    deprovision_job,
    provision_job,
    validate_docker_image,
)
from grandchallenge.components.validators import (
    validate_no_slash_at_ends,
    validate_safe_path,
)
from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
)
from grandchallenge.core.validators import (
    ExtensionValidator,
    JSONSchemaValidator,
    JSONValidator,
    MimeTypeValidator,
)
from grandchallenge.uploads.models import UserUpload

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_INTERFACE_SLUG = "generic-overlay"


class InterfaceKindChoices(models.TextChoices):
    """Interface kind choices."""

    STRING = "STR", _("String")
    INTEGER = "INT", _("Integer")
    FLOAT = "FLT", _("Float")
    BOOL = "BOOL", _("Bool")
    ANY = "JSON", _("Anything")
    CHART = "CHART", _("Chart")

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

    # File types
    PDF = "PDF", _("PDF file")
    SQREG = "SQREG", _("SQREG file")
    THUMBNAIL_JPG = "JPEG", _("Thumbnail jpg")
    THUMBNAIL_PNG = "PNG", _("Thumbnail png")

    # Legacy support
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
    def interface_type_json():
        """Interface kinds that are json serializable:

        * String
        * Integer
        * Float
        * Bool
        * Anything that is JSON serializable (any object)
        * 2D bounding box
        * Multiple 2D bounding boxes
        * Distance measurement
        * Multiple distance measurements
        * Point
        * Multiple points
        * Polygon
        * Multiple polygons
        * Choice (string)
        * Multiple choice (array of strings)
        * Chart

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

        Example json for Chart

        .. code-block:: json

            {
                "description": "A simple bar chart with embedded data.",
                "data": {
                    "values": [
                        {"a": "A", "b": 28}, {"a": "B", "b": 55}, {"a": "C", "b": 43},
                        {"a": "D", "b": 91}, {"a": "E", "b": 81}, {"a": "F", "b": 53},
                        {"a": "G", "b": 19}, {"a": "H", "b": 87}, {"a": "I", "b": 52}
                    ]
                },
                "mark": "bar",
                "encoding": {
                    "x": {"field": "a", "type": "nominal", "axis": {"labelAngle": 0}},
                    "y": {"field": "b", "type": "quantitative"}
                }
            }

        """
        return (
            InterfaceKind.InterfaceKindChoices.STRING,
            InterfaceKind.InterfaceKindChoices.INTEGER,
            InterfaceKind.InterfaceKindChoices.FLOAT,
            InterfaceKind.InterfaceKindChoices.BOOL,
            InterfaceKind.InterfaceKindChoices.TWO_D_BOUNDING_BOX,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
            InterfaceKind.InterfaceKindChoices.DISTANCE_MEASUREMENT,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
            InterfaceKind.InterfaceKindChoices.POINT,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_POINTS,
            InterfaceKind.InterfaceKindChoices.POLYGON,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_POLYGONS,
            InterfaceKind.InterfaceKindChoices.CHOICE,
            InterfaceKind.InterfaceKindChoices.MULTIPLE_CHOICE,
            InterfaceKind.InterfaceKindChoices.ANY,
            InterfaceKind.InterfaceKindChoices.CHART,
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
    def interface_type_file():
        """Interface kinds that are files:

        * CSV file
        * ZIP file
        * PDF file
        * SQREG file
        * Thumbnail JPG
        * Thumbnail PNG
        """
        return (
            InterfaceKind.InterfaceKindChoices.CSV,
            InterfaceKind.InterfaceKindChoices.ZIP,
            InterfaceKind.InterfaceKindChoices.PDF,
            InterfaceKind.InterfaceKindChoices.SQREG,
            InterfaceKind.InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKind.InterfaceKindChoices.THUMBNAIL_PNG,
        )

    @classmethod
    def get_default_field(cls, *, kind):
        if kind in {*cls.interface_type_file()}:
            return ModelChoiceField
        elif kind in {*cls.interface_type_image()}:
            return ModelMultipleChoiceField
        elif kind in {
            InterfaceKind.InterfaceKindChoices.STRING,
            InterfaceKind.InterfaceKindChoices.CHOICE,
        }:
            return forms.CharField
        elif kind == InterfaceKind.InterfaceKindChoices.INTEGER:
            return forms.IntegerField
        elif kind == InterfaceKind.InterfaceKindChoices.FLOAT:
            return forms.FloatField
        elif kind == InterfaceKind.InterfaceKindChoices.BOOL:
            return forms.BooleanField
        else:
            return forms.JSONField

    @classmethod
    def get_file_mimetypes(cls, *, kind):
        if kind == InterfaceKind.InterfaceKindChoices.CSV:
            return (
                "application/csv",
                "application/vnd.ms-excel",
                "text/csv",
                "text/plain",
            )
        elif kind == InterfaceKind.InterfaceKindChoices.ZIP:
            return (
                "application/zip",
                "application/x-zip-compressed",
            )
        elif kind == InterfaceKind.InterfaceKindChoices.PDF:
            return ("application/pdf",)
        elif kind == InterfaceKind.InterfaceKindChoices.THUMBNAIL_JPG:
            return ("image/jpeg",)
        elif kind == InterfaceKind.InterfaceKindChoices.THUMBNAIL_PNG:
            return ("image/png",)
        elif kind == InterfaceKind.InterfaceKindChoices.SQREG:
            return ("application/vnd.sqlite3",)
        else:
            raise RuntimeError(f"Unknown kind {kind}")


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
    schema = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Additional JSON schema that the values for this interface must "
            "satisfy. See https://json-schema.org/. "
            "Only Draft 7, 6, 4 or 3 are supported."
        ),
        validators=[JSONSchemaValidator()],
    )
    kind = models.CharField(
        blank=False,
        max_length=5,
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
        validators=[
            validate_safe_path,
            validate_no_slash_at_ends,
            # No uuids in path
            RegexValidator(
                regex=r".*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}.*",
                inverse_match=True,
                flags=re.IGNORECASE,
            ),
        ],
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
        # CSV, ZIP, PDF, SQREG and Thumbnail should always be saved to S3, others are optional
        return (
            self.is_image_kind
            or self.kind in InterfaceKind.interface_type_file()
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

    def clean(self):
        super().clean()
        self._clean_store_in_database()
        self._clean_relative_path()

    def _clean_relative_path(self):
        if self.kind in InterfaceKind.interface_type_json():
            if not self.relative_path.endswith(".json"):
                raise ValidationError("Relative path should end with .json")
        elif self.kind in InterfaceKind.interface_type_file() and not self.relative_path.endswith(
            f".{self.kind.lower()}"
        ):
            raise ValidationError(
                f"Relative path should end with .{self.kind.lower()}"
            )

        if self.kind in InterfaceKind.interface_type_image():
            if not self.relative_path.startswith("images/"):
                raise ValidationError(
                    "Relative path should start with images/"
                )
            if Path(self.relative_path).name != Path(self.relative_path).stem:
                # Maybe not in the future
                raise ValidationError("Images should be a directory")
        else:
            if self.relative_path.startswith("images/"):
                raise ValidationError(
                    "Relative path should not start with images/"
                )

    def _clean_store_in_database(self):
        if (
            self.kind not in InterfaceKind.interface_type_json()
            and self.store_in_database
        ):
            raise ValidationError(
                f"Interface {self.kind} objects cannot be stored in the database"
            )

    def validate_against_schema(self, *, value):
        """Validates values against both default and custom schemas"""
        JSONValidator(
            schema={
                **INTERFACE_VALUE_SCHEMA,
                "anyOf": [{"$ref": f"#/definitions/{self.kind}"}],
            }
        )(value=value)

        if self.schema:
            JSONValidator(schema=self.schema)(value=value)

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
            ExtensionValidator(
                allowed_extensions=(
                    ".json",
                    ".zip",
                    ".csv",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".pdf",
                    ".sqreg",
                )
            ),
            MimeTypeValidator(
                allowed_types=(
                    "application/json",
                    "application/zip",
                    "text/plain",
                    "application/csv",
                    "application/pdf",
                    "image/png",
                    "image/jpeg",
                    "application/vnd.sqlite3",
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

    def clean(self):
        super().clean()

        if self.interface.kind in InterfaceKind.interface_type_image():
            self._validate_image_only()
        elif self.interface.kind in InterfaceKind.interface_type_file():
            self._validate_file_only()
        else:
            self._validate_value()

    def _validate_image_only(self):
        if not self.image:
            raise ValidationError("Image must be set")
        if self.file or self.value is not None:
            raise ValidationError(
                f"File ({self.file}) or value should not be set for images"
            )

    def _validate_file_only(self):
        if not self.file:
            raise ValidationError("File must be set")
        if self.image or self.value is not None:
            raise ValidationError(
                f"Image ({self.image}) or value must not be set for files"
            )

    def _validate_value_only(self):
        # Do not check self.value here, it can be anything including None.
        # This is checked later with interface.validate_against_schema.
        if self.image or self.file:
            raise ValidationError(
                f"Image ({self.image}) or file ({self.file}) must not be set for values"
            )

    def _validate_value(self):
        if self.interface.save_in_object_store:
            self._validate_file_only()
            with self.file.open("r") as f:
                value = json.loads(f.read().decode("utf-8"))
        else:
            self._validate_value_only()
            value = self.value

        self.interface.validate_against_schema(value=value)

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
    PROVISIONING = 6
    PROVISIONED = 7
    EXECUTING = 8
    EXECUTED = 9
    PARSING = 10
    EXECUTING_PREREQUISITES = 11

    STATUS_CHOICES = (
        (PENDING, "Queued"),
        (STARTED, "Started"),
        (RETRY, "Re-Queued"),
        (FAILURE, "Failed"),
        (SUCCESS, "Succeeded"),
        (CANCELLED, "Cancelled"),
        (PROVISIONING, "Provisioning"),
        (PROVISIONED, "Provisioned"),
        (EXECUTING, "Executing"),
        (EXECUTED, "Executed"),
        (PARSING, "Parsing Outputs"),
        (EXECUTING_PREREQUISITES, "Executing Algorithm"),
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
            "/input/foo/bar/<relative_path>"
        ),
    )
    task_on_success = models.JSONField(
        default=None,
        null=True,
        editable=False,
        help_text="Serialized task that is run on job success",
    )
    task_on_failure = models.JSONField(
        default=None,
        null=True,
        editable=False,
        help_text="Serialized task that is run on job failure",
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
        duration: Optional[timedelta] = None,
    ):
        self.status = status

        if stdout:
            self.stdout = stdout

        if stderr:
            self.stderr = stderr

        if error_message:
            self.error_message = error_message[:1024]

        if (
            status in [self.STARTED, self.EXECUTING]
            and self.started_at is None
        ):
            self.started_at = now()
        elif (
            status
            in [self.EXECUTED, self.SUCCESS, self.FAILURE, self.CANCELLED]
            and self.completed_at is None
        ):
            self.completed_at = now()
            if duration and self.started_at:
                # TODO: maybe add separate timings for provisioning, executing, parsing and total
                self.started_at = self.completed_at - duration

        self.save()

        if self.status == self.SUCCESS:
            on_commit(self.execute_task_on_success)
        elif self.status in [self.FAILURE, self.CANCELLED]:
            on_commit(self.execute_task_on_failure)

    @property
    def executor_kwargs(self):
        return {
            "job_id": f"{self._meta.app_label}-{self._meta.model_name}-{self.pk}",
            "exec_image_sha256": self.container.image_sha256,
            "exec_image_repo_tag": self.container.repo_tag,
            "exec_image_file": self.container.image,
            "memory_limit": self.container.requires_memory_gb,
            "requires_gpu": self.container.requires_gpu,
        }

    def get_executor(self, *, backend):
        Executor = import_string(backend)  # noqa: N806
        return Executor(**self.executor_kwargs)

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
    def signature_kwargs(self):
        return {
            "kwargs": {
                "job_pk": str(self.pk),
                "job_app_label": self._meta.app_label,
                "job_model_name": self._meta.model_name,
                "backend": settings.COMPONENTS_DEFAULT_BACKEND,
            },
            "immutable": True,
        }

    def execute(self):
        return provision_job.signature(**self.signature_kwargs).apply_async()

    def execute_task_on_success(self):
        deprovision_job.signature(**self.signature_kwargs).apply_async()
        if self.task_on_success:
            signature(self.task_on_success).apply_async()

    def execute_task_on_failure(self):
        deprovision_job.signature(**self.signature_kwargs).apply_async()
        if self.task_on_failure:
            signature(self.task_on_failure).apply_async()

    @property
    def animate(self):
        return self.status in {
            self.STARTED,
            self.PROVISIONING,
            self.PROVISIONED,
            self.EXECUTING,
            self.EXECUTED,
            self.PARSING,
            self.EXECUTING_PREREQUISITES,
        }

    @property
    def status_context(self):
        if self.status == self.SUCCESS:
            if self.stderr:
                return "warning"
            else:
                return "success"
        elif self.status in {self.FAILURE, self.CANCELLED}:
            return "danger"
        elif self.status in {
            self.PENDING,
            self.STARTED,
            self.RETRY,
            self.PROVISIONING,
            self.PROVISIONED,
            self.EXECUTING,
            self.EXECUTED,
            self.PARSING,
            self.EXECUTING_PREREQUISITES,
        }:
            return "info"
        else:
            return "secondary"

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
    user_upload = models.ForeignKey(
        UserUpload, blank=True, null=True, on_delete=models.SET_NULL,
    )
    image = models.FileField(
        blank=True,
        upload_to=docker_image_path,
        validators=[
            ExtensionValidator(
                allowed_extensions=(".tar", ".tar.gz", ".tar.xz")
            )
        ],
        help_text=(
            ".tar.xz archive of the container image produced from the command "
            "'docker save IMAGE | xz -c > IMAGE.tar.xz'. See "
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

    @property
    def repo_tag(self):
        """The tag of this image in the container repository"""
        return (
            f"{settings.COMPONENTS_REGISTRY_URL}/"
            f"{settings.COMPONENTS_REGISTRY_PREFIX}/"
            f"{self._meta.app_label}/{self._meta.model_name}:{self.pk}"
        )

    class Meta:
        abstract = True
