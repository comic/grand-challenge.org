import json
import logging
import re
import secrets
from enum import Enum
from json import JSONDecodeError
from pathlib import Path
from tempfile import NamedTemporaryFile

from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import signature
from django import forms
from django.conf import settings
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError,
)
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models, transaction
from django.db.models import IntegerChoices, QuerySet
from django.db.transaction import on_commit
from django.forms import ModelChoiceField
from django.template.defaultfilters import truncatewords
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _
from django_deprecate_fields import deprecate_field
from django_extensions.db.fields import AutoSlugField
from panimg.models import MAXIMUM_SEGMENTS_LENGTH

from grandchallenge.cases.models import (
    DICOMImageSetUpload,
    Image,
    ImageFile,
    RawImageUploadSession,
)
from grandchallenge.charts.specs import components_line
from grandchallenge.components.backends.exceptions import (
    CINotAllowedException,
    CIVNotEditableException,
)
from grandchallenge.components.schemas import (
    GPUTypeChoices,
    generate_component_json_schema,
)
from grandchallenge.components.tasks import (
    _repo_login_and_run,
    assign_docker_image_from_upload,
    deprovision_job,
    provision_job,
    validate_docker_image,
)
from grandchallenge.components.validators import (
    validate_biom_format,
    validate_newick_tree_format,
    validate_no_slash_at_ends,
    validate_relative_path_not_reserved,
    validate_safe_path,
)
from grandchallenge.core.celery import acks_late_2xlarge_task
from grandchallenge.core.error_handlers import (
    DICOMImageSetUploadErrorHandler,
    EvaluationCIVErrorHandler,
    FallbackCIVValidationErrorHandler,
    JobCIVErrorHandler,
    RawImageUploadSessionErrorHandler,
    UserUploadCIVErrorHandler,
)
from grandchallenge.core.models import FieldChangeMixin, UUIDModel
from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
)
from grandchallenge.core.utils.error_messages import (
    format_validation_error_message,
)
from grandchallenge.core.validators import (
    ExtensionValidator,
    JSONSchemaValidator,
    JSONValidator,
    MimeTypeValidator,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.validators import validate_gzip_mimetype
from grandchallenge.workstation_configs.models import (
    OVERLAY_SEGMENTS_SCHEMA,
    LookUpTable,
)

logger = logging.getLogger(__name__)


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
    LINE = "LINE", _("Line")
    MULTIPLE_LINES = "MLIN", _("Multiple lines")
    ANGLE = "ANGL", _("Angle")
    MULTIPLE_ANGLES = "MANG", _("Multiple angles")
    ELLIPSE = "ELLI", _("Ellipse")
    MULTIPLE_ELLIPSES = "MELL", _("Multiple ellipses")
    THREE_POINT_ANGLE = "3ANG", _("Three-point angle")
    MULTIPLE_THREE_POINT_ANGLES = "M3AN", _("Multiple three-point angles")

    # Registration types
    AFFINE_TRANSFORM_REGISTRATION = "ATRG", _("Affine transform registration")

    # Choice Types
    CHOICE = "CHOI", _("Choice")
    MULTIPLE_CHOICE = "MCHO", _("Multiple choice")

    # Image types
    PANIMG_IMAGE = "IMG", _("Image")
    PANIMG_SEGMENTATION = "SEG", _("Segmentation")
    PANIMG_HEAT_MAP = "HMAP", _("Heat Map")
    PANIMG_DISPLACEMENT_FIELD = "DSPF", _("Displacement field")
    DICOM_IMAGE_SET = "DCMIS", _("DICOM Image Set")

    # File types
    PDF = "PDF", _("PDF file")
    SQREG = "SQREG", _("SQREG file")
    THUMBNAIL_JPG = "JPEG", _("Thumbnail jpg")
    THUMBNAIL_PNG = "PNG", _("Thumbnail png")
    OBJ = "OBJ", _("OBJ file")
    MP4 = "MP4", _("MP4 file")
    NEWICK = "NEWCK", _("Newick tree-format file")
    BIOM = "BIOM", _("BIOM format")

    # Legacy support
    CSV = "CSV", _("CSV file")
    ZIP = "ZIP", _("ZIP file")


class InterfaceSuperKindChoices(models.TextChoices):
    IMAGE = "I", "Image"
    FILE = "F", "File"
    VALUE = "V", "Value"


class InterfaceKinds(set, Enum):
    r"""Interface kind sets.

    .. exec_code::
        :hide_code:

        import json
        import os

        import django

        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        django.setup()

        from grandchallenge.components.models import InterfaceKinds
        from grandchallenge.components.models import INTERFACE_KIND_JSON_EXAMPLES

        print("Interface kinds that are images:\n")
        for member in InterfaceKinds.image:
            print("  -", member.label)
        print("\n")

        print("Interface kinds that are files:\n")
        for member in InterfaceKinds.file:
            print("  -", member.label)
        print("\n")

        print("Interface kinds that are json serializable:\n")
        for member in InterfaceKinds.json:
            print("  -", member.label)
        print("\n")

        for key, example in INTERFACE_KIND_JSON_EXAMPLES.items():
            title = f"Example JSON file contents for {key.label}"

            if example.extra_info:
                title += f" ({example.extra_info})"

            print(f"{title}:")
            print(json.dumps(example.value, indent=2))
            print("")
    """

    json = {
        InterfaceKindChoices.STRING,
        InterfaceKindChoices.INTEGER,
        InterfaceKindChoices.FLOAT,
        InterfaceKindChoices.BOOL,
        InterfaceKindChoices.TWO_D_BOUNDING_BOX,
        InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
        InterfaceKindChoices.DISTANCE_MEASUREMENT,
        InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
        InterfaceKindChoices.POINT,
        InterfaceKindChoices.MULTIPLE_POINTS,
        InterfaceKindChoices.POLYGON,
        InterfaceKindChoices.MULTIPLE_POLYGONS,
        InterfaceKindChoices.CHOICE,
        InterfaceKindChoices.MULTIPLE_CHOICE,
        InterfaceKindChoices.ANY,
        InterfaceKindChoices.CHART,
        InterfaceKindChoices.LINE,
        InterfaceKindChoices.MULTIPLE_LINES,
        InterfaceKindChoices.ANGLE,
        InterfaceKindChoices.MULTIPLE_ANGLES,
        InterfaceKindChoices.ELLIPSE,
        InterfaceKindChoices.MULTIPLE_ELLIPSES,
        InterfaceKindChoices.THREE_POINT_ANGLE,
        InterfaceKindChoices.MULTIPLE_THREE_POINT_ANGLES,
        InterfaceKindChoices.AFFINE_TRANSFORM_REGISTRATION,
    }

    image = {
        InterfaceKindChoices.PANIMG_IMAGE,
        InterfaceKindChoices.PANIMG_HEAT_MAP,
        InterfaceKindChoices.PANIMG_SEGMENTATION,
        InterfaceKindChoices.PANIMG_DISPLACEMENT_FIELD,
        InterfaceKindChoices.DICOM_IMAGE_SET,
    }

    file = {
        InterfaceKindChoices.CSV,
        InterfaceKindChoices.ZIP,
        InterfaceKindChoices.PDF,
        InterfaceKindChoices.SQREG,
        InterfaceKindChoices.THUMBNAIL_JPG,
        InterfaceKindChoices.THUMBNAIL_PNG,
        InterfaceKindChoices.OBJ,
        InterfaceKindChoices.MP4,
        InterfaceKindChoices.NEWICK,
        InterfaceKindChoices.BIOM,
    }

    # Interfaces that can only be displayed in isolation.
    mandatory_isolation = {
        InterfaceKindChoices.CHART,
        InterfaceKindChoices.PDF,
        InterfaceKindChoices.THUMBNAIL_JPG,
        InterfaceKindChoices.THUMBNAIL_PNG,
        InterfaceKindChoices.MP4,
    }

    # Interfaces that cannot be displayed.
    undisplayable = {
        InterfaceKindChoices.CSV,
        InterfaceKindChoices.ZIP,
        InterfaceKindChoices.OBJ,
        InterfaceKindChoices.NEWICK,
        InterfaceKindChoices.BIOM,
    }

    panimg = {
        InterfaceKindChoices.PANIMG_IMAGE,
        InterfaceKindChoices.PANIMG_HEAT_MAP,
        InterfaceKindChoices.PANIMG_SEGMENTATION,
        InterfaceKindChoices.PANIMG_DISPLACEMENT_FIELD,
    }


class OverlaySegmentsMixin(models.Model):
    overlay_segments = models.JSONField(
        blank=True,
        default=list,
        help_text=(
            "The schema that defines how categories of values in the overlay images are differentiated. "
            'Example usage: [{"name": "background", "visible": true, "voxel_value": 0},'
            '{"name": "tissue", "visible": true, "voxel_value": 1}]. '
            "If a categorical overlay is shown, "
            "it is possible to show toggles to change the visibility of the different overlay categories. "
            "To do so, configure the categories that should be displayed. "
            'For example: [{"name": "Level 0", "visible": false, "voxel_value": 0].'
        ),
        validators=[JSONValidator(schema=OVERLAY_SEGMENTS_SCHEMA)],
    )
    look_up_table = models.ForeignKey(
        to=LookUpTable,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The look-up table that is applied when an overlay image is first shown",
    )

    @property
    def overlay_segments_allowed_values(self):
        allowed_values = {x["voxel_value"] for x in self.overlay_segments}
        # An implicit background value of 0 is always allowed, this saves the
        # user having to declare it and the annotator mark it
        allowed_values.add(0)

        return allowed_values

    @property
    def overlay_segments_is_contiguous(self):
        values = sorted(list(self.overlay_segments_allowed_values))
        return all(
            values[i] - values[i - 1] == 1 for i in range(1, len(values))
        )

    def _validate_voxel_values(self, image):
        if not self.overlay_segments:
            return

        if image.segments is None:
            raise ValidationError(
                "Image segments could not be determined, ensure the voxel values "
                "are integers and that it contains no more than "
                f"{MAXIMUM_SEGMENTS_LENGTH} segments. Ensure the image has the "
                "minimum and maximum voxel values set as tags if the image is a TIFF "
                "file."
            )

        invalid_values = (
            set(image.segments) - self.overlay_segments_allowed_values
        )
        if invalid_values:
            raise ValidationError(
                f"The valid voxel values for this segmentation are: "
                f"{self.overlay_segments_allowed_values}. This segmentation is "
                f"invalid as it contains the voxel values: {invalid_values}."
            )

    def _validate_vector_field(self, image: Image):
        if len(image.shape) != 4:
            raise ValidationError(
                "Deformation and displacement must be 4D images."
            )
        if image.shape_without_color != image.shape:
            raise ValidationError(
                "Deformation and displacement fields cannot have a color component."
            )
        if image.shape[0] != 3:
            raise ValidationError(
                "Deformation and displacement field's 4th dimension "
                "must be a 3-component vector."
            )

    class Meta:
        abstract = True


class ComponentInterface(OverlaySegmentsMixin):
    Kind = InterfaceKindChoices
    SuperKind = InterfaceSuperKindChoices

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
            validate_relative_path_not_reserved,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._overlay_segments_orig = self.overlay_segments

    def __str__(self):
        return f"{self.title} ({self.get_kind_display()})"

    @property
    def is_image_kind(self):
        return self.kind in InterfaceKinds.image

    @property
    def is_panimg_kind(self):
        return self.kind in InterfaceKinds.panimg

    @property
    def is_dicom_image_kind(self):
        return self.kind == InterfaceKindChoices.DICOM_IMAGE_SET

    @property
    def is_json_kind(self):
        return self.kind in InterfaceKinds.json

    @property
    def is_file_kind(self):
        return self.kind in InterfaceKinds.file

    @property
    def is_thumbnail_kind(self):
        return self.kind in [
            InterfaceKindChoices.THUMBNAIL_JPG,
            InterfaceKindChoices.THUMBNAIL_PNG,
        ]

    @property
    def is_previewable(self):
        return self.store_in_database and self.kind in [
            InterfaceKindChoices.BOOL,
            InterfaceKindChoices.FLOAT,
            InterfaceKindChoices.INTEGER,
            InterfaceKindChoices.STRING,
        ]

    @property
    def json_kind_example(self):
        try:
            return self.example_value
        except ObjectDoesNotExist:
            return INTERFACE_KIND_JSON_EXAMPLES.get(self.kind)

    @property
    def super_kind(self):
        if self.is_image_kind:
            return InterfaceSuperKindChoices.IMAGE
        elif self.is_json_kind and self.store_in_database:
            return InterfaceSuperKindChoices.VALUE
        else:
            return InterfaceSuperKindChoices.FILE

    @property
    def default_field(self):
        if self.super_kind in (
            InterfaceSuperKindChoices.FILE,
            InterfaceSuperKindChoices.IMAGE,
        ):
            return ModelChoiceField
        elif self.kind in {
            InterfaceKindChoices.STRING,
            InterfaceKindChoices.CHOICE,
        }:
            return forms.CharField
        elif self.kind == InterfaceKindChoices.INTEGER:
            return forms.IntegerField
        elif self.kind == InterfaceKindChoices.FLOAT:
            return forms.FloatField
        elif self.kind == InterfaceKindChoices.BOOL:
            return forms.BooleanField
        else:
            return forms.JSONField

    @property
    def allowed_file_types(self):
        """The allowed file types of the interface that is relevant when uploading"""
        try:
            return INTERFACE_KIND_TO_ALLOWED_FILE_TYPES[self.kind]
        except KeyError as e:
            raise RuntimeError(f"Unknown kind {self.kind}") from e

    @property
    def file_extension(self):
        """The dot filename extension (e.g. '.jpg') of an interface that is relevant when writing"""
        try:
            return INTERFACE_KIND_TO_FILE_EXTENSION[self.kind]
        except KeyError as e:
            raise RuntimeError(f"Unknown kind {self.kind}") from e

    def create_instance(self, *, image=None, value=None, fileobj=None):
        civ = ComponentInterfaceValue.objects.create(interface=self)

        if image:
            civ.image = image
        elif fileobj:
            container = File(fileobj)
            civ.file.save(Path(self.relative_path).name, container)
        elif not self.store_in_database:
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
        self._clean_overlay_segments()
        self._clean_store_in_database()
        self._clean_relative_path()
        self._clean_example_value()
        self._clean_default_value()

    def _clean_overlay_segments(self):
        from grandchallenge.reader_studies.models import Question

        if (
            self.kind == InterfaceKindChoices.PANIMG_SEGMENTATION
            and not self.overlay_segments
        ):
            raise ValidationError(
                "Overlay segments must be set for this interface"
            )

        if (
            self.kind != InterfaceKindChoices.PANIMG_SEGMENTATION
            and self.overlay_segments
        ):
            raise ValidationError(
                "Overlay segments should only be set for segmentations"
            )

        if not self.overlay_segments_is_contiguous:
            raise ValidationError(
                "Voxel values for overlay segments must be contiguous."
            )

        if (
            self.pk is not None
            and self._overlay_segments_orig != self.overlay_segments
            and not self._overlay_segments_preserved
            and (
                ComponentInterfaceValue.objects.filter(interface=self).exists()
                or Question.objects.filter(interface=self).exists()
            )
        ):
            raise ValidationError(
                "Overlay segments cannot be changed, as values or questions "
                "for this ComponentInterface exist."
            )

    @property
    def _overlay_segments_preserved(self):
        orig_overlay_segments = {
            tuple(sorted(d.items())) for d in self._overlay_segments_orig
        }
        new_overlay_segments = {
            tuple(sorted(d.items())) for d in self.overlay_segments
        }
        return orig_overlay_segments <= new_overlay_segments

    def _clean_relative_path(self):
        if (
            self.is_file_kind or self.is_json_kind
        ) and not self.relative_path.endswith(self.file_extension):
            raise ValidationError(
                f"Relative path should end with {self.file_extension}"
            )

        if self.is_image_kind:
            if not self.relative_path.startswith("images/"):
                raise ValidationError(
                    "Relative path should start with images/"
                )
            if Path(self.relative_path).name != Path(self.relative_path).stem:
                raise ValidationError("Images should be a directory")
        else:
            if self.relative_path.startswith("images/"):
                raise ValidationError(
                    "Relative path should not start with images/"
                )

    def _clean_store_in_database(self):
        allow_store_in_database = self.kind in (
            InterfaceKinds.json.difference(
                {
                    # These values can be large, so for any new interfaces
                    # of this type do not allow storing in the database.
                    InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
                    InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
                    InterfaceKindChoices.MULTIPLE_POINTS,
                    InterfaceKindChoices.MULTIPLE_POLYGONS,
                    InterfaceKindChoices.MULTIPLE_LINES,
                    InterfaceKindChoices.MULTIPLE_ANGLES,
                    InterfaceKindChoices.MULTIPLE_ELLIPSES,
                    InterfaceKindChoices.MULTIPLE_THREE_POINT_ANGLES,
                }
            )
        )

        if self.store_in_database and not allow_store_in_database:
            raise ValidationError(
                f"Interface {self.kind} objects cannot be stored in the database"
            )

    def _clean_example_value(self):
        try:
            self.example_value.full_clean()
        except ObjectDoesNotExist:
            pass
        except ValidationError as error:
            raise ValidationError(
                f"The example value for this interface is not valid: {error}"
            )

    def _clean_default_value(self):
        if (
            self.super_kind == InterfaceSuperKindChoices.FILE
            and self.default_value
        ):
            raise ValidationError(
                "A socket that requires a file should not have a default value"
            )

    def validate_against_schema(self, *, value):
        """Validates values against both default and custom schemas"""
        schema = generate_component_json_schema(
            component_interface=self, required=True
        )
        JSONValidator(schema=schema)(value=value)

    @cached_property
    def value_required(self):
        value_required = True
        if self.kind == InterfaceKindChoices.BOOL:
            value_required = False
        elif self.super_kind == InterfaceSuperKindChoices.VALUE:
            try:
                self.validate_against_schema(value=None)
                value_required = False
            except ValidationError:
                pass
        return value_required

    class Meta:
        ordering = ("pk",)


class ComponentInterfaceExampleValue(UUIDModel):
    interface = models.OneToOneField(
        to=ComponentInterface,
        on_delete=models.CASCADE,
        related_name="example_value",
    )
    value = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Example value for an interface",
    )
    extra_info = models.TextField(
        blank=True, help_text="Extra information about the example value"
    )

    def clean(self):
        super().clean()

        if self.interface.is_json_kind:
            civ = ComponentInterfaceValue(interface=self.interface)

            if self.interface.store_in_database:
                civ.value = self.value
            else:
                file = ContentFile(
                    json.dumps(self.value).encode("utf-8"),
                    name=f"{self.interface.kind}.json",
                )
                civ.file = file

            civ.full_clean()
        else:
            raise ValidationError(
                "Example value can be set for interfaces of JSON kind only"
            )


INTERFACE_KIND_JSON_EXAMPLES = {
    InterfaceKindChoices.STRING: ComponentInterfaceExampleValue(
        value="Example String"
    ),
    InterfaceKindChoices.INTEGER: ComponentInterfaceExampleValue(value=42),
    InterfaceKindChoices.FLOAT: ComponentInterfaceExampleValue(value=42.0),
    InterfaceKindChoices.BOOL: ComponentInterfaceExampleValue(value=True),
    InterfaceKindChoices.ANY: ComponentInterfaceExampleValue(
        value={"key": "value", "None": None}
    ),
    InterfaceKindChoices.CHART: ComponentInterfaceExampleValue(
        value={
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": 300,
            "height": 300,
            "data": {
                "values": [
                    {
                        "target": "Negative",
                        "prediction": "Negative",
                        "value": 198,
                    },
                    {
                        "target": "Negative",
                        "prediction": "Positive",
                        "value": 9,
                    },
                    {
                        "target": "Positive",
                        "prediction": "Negative",
                        "value": 159,
                    },
                    {
                        "target": "Positive",
                        "prediction": "Positive",
                        "value": 376,
                    },
                ],
                "format": {"type": "json"},
            },
            "layer": [
                {
                    "mark": "rect",
                    "encoding": {
                        "y": {"field": "target", "type": "ordinal"},
                        "x": {"field": "prediction", "type": "ordinal"},
                        "color": {
                            "field": "value",
                            "type": "quantitative",
                            "title": "Count of Records",
                            "legend": {
                                "direction": "vertical",
                                "gradientLength": 300,
                            },
                        },
                    },
                },
                {
                    "mark": "text",
                    "encoding": {
                        "y": {"field": "target", "type": "ordinal"},
                        "x": {"field": "prediction", "type": "ordinal"},
                        "text": {"field": "value", "type": "quantitative"},
                        "color": {
                            "condition": {
                                "test": "datum['value'] < 40",
                                "value": "black",
                            },
                            "value": "white",
                        },
                    },
                },
            ],
            "config": {"axis": {"grid": True, "tickBand": "extent"}},
        },
        extra_info="For more examples, see https://vega.github.io/vega-lite/examples/",
    ),
    InterfaceKindChoices.TWO_D_BOUNDING_BOX: ComponentInterfaceExampleValue(
        value={
            "name": "Region of interest",
            "type": "2D bounding box",
            "corners": [
                [130.8, 148.8, 0.5],
                [69.7, 148.8, 0.5],
                [69.7, 73.1, 0.5],
                [130.8, 73.1, 0.5],
            ],
            "probability": 0.95,
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES: ComponentInterfaceExampleValue(
        value={
            "name": "Regions of interest",
            "type": "Multiple 2D bounding boxes",
            "boxes": [
                {
                    "name": "ROI 1",
                    "corners": [
                        [92.6, 136.0, 0.5],
                        [54.8, 136.0, 0.5],
                        [54.8, 95.5, 0.5],
                        [92.6, 95.5, 0.5],
                    ],
                    "probability": 0.95,
                },
                {
                    "name": "ROI 2",
                    "corners": [
                        [92.6, 136.0, 0.5],
                        [54.8, 136.0, 0.5],
                        [54.8, 95.5, 0.5],
                        [92.6, 95.5, 0.5],
                    ],
                    "probability": 0.92,
                },
            ],
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.DISTANCE_MEASUREMENT: ComponentInterfaceExampleValue(
        value={
            "name": "Distance between areas",
            "type": "Distance measurement",
            "start": [59.8, 78.8, 0.5],
            "end": [69.4, 143.8, 0.5],
            "probability": 0.92,
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS: ComponentInterfaceExampleValue(
        value={
            "name": "Distances between areas",
            "type": "Multiple distance measurements",
            "lines": [
                {
                    "name": "Distance 1",
                    "start": [49.7, 103.3, 0.5],
                    "end": [55.1, 139.3, 0.5],
                    "probability": 0.92,
                },
                {
                    "name": "Distance 2",
                    "start": [49.7, 103.3, 0.5],
                    "end": [55.1, 139.3, 0.5],
                    "probability": 0.92,
                },
            ],
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.POINT: ComponentInterfaceExampleValue(
        value={
            "name": "Point of interest",
            "type": "Point",
            "point": [152.1, 111.0, 0.5],
            "probability": 0.92,
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.MULTIPLE_POINTS: ComponentInterfaceExampleValue(
        value={
            "name": "Points of interest",
            "type": "Multiple points",
            "points": [
                {
                    "name": "Point 1",
                    "point": [96.0, 79.8, 0.5],
                    "probability": 0.92,
                },
                {
                    "name": "Point 2",
                    "point": [130.1, 115.5, 0.5],
                    "probability": 0.92,
                },
            ],
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.POLYGON: ComponentInterfaceExampleValue(
        value={
            "name": "Area of interest",
            "type": "Polygon",
            "seed_point": [76.4, 124.0, 0.5],
            "path_points": [
                [76.41, 124.01, 0.5],
                [76.41, 124.05, 0.5],
                [76.42, 124.08, 0.5],
            ],
            "sub_type": "brush",
            "groups": [],
            "probability": 0.92,
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.MULTIPLE_POLYGONS: ComponentInterfaceExampleValue(
        value={
            "name": "Areas of interest",
            "type": "Multiple polygons",
            "polygons": [
                {
                    "name": "Area 1",
                    "seed_point": [55.82, 90.46, 0.5],
                    "path_points": [
                        [55.82, 90.46, 0.5],
                        [55.93, 90.88, 0.5],
                        [56.24, 91.19, 0.5],
                        [56.66, 91.30, 0.5],
                    ],
                    "sub_type": "brush",
                    "groups": ["manual"],
                    "probability": 0.67,
                },
                {
                    "name": "Area 2",
                    "seed_point": [90.22, 96.06, 0.5],
                    "path_points": [
                        [90.22, 96.06, 0.5],
                        [90.33, 96.48, 0.5],
                        [90.64, 96.79, 0.5],
                    ],
                    "sub_type": "brush",
                    "groups": [],
                    "probability": 0.92,
                },
            ],
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.LINE: ComponentInterfaceExampleValue(
        value={
            "name": "Some annotation",
            "type": "Line",
            "seed_points": [[1, 2, 3], [1, 2, 3]],
            "path_point_lists": [
                [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
            ],
            "probability": 0.92,
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.MULTIPLE_LINES: ComponentInterfaceExampleValue(
        value={
            "name": "Some annotations",
            "type": "Multiple lines",
            "lines": [
                {
                    "name": "Annotation 1",
                    "seed_points": [[1, 2, 3], [1, 2, 3]],
                    "path_point_lists": [
                        [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                        [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                    ],
                    "probability": 0.78,
                },
                {
                    "name": "Annotation 2",
                    "seed_points": [[1, 2, 3], [1, 2, 3]],
                    "path_point_lists": [
                        [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                        [[5, 6, 7], [8, 9, 10], [1, 0, 10], [2, 4, 2]],
                    ],
                    "probability": 0.92,
                },
            ],
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.ANGLE: ComponentInterfaceExampleValue(
        value={
            "name": "Some angle",
            "type": "Angle",
            "lines": [
                [[180, 10, 0.5], [190, 10, 0.5]],
                [[180, 25, 0.5], [190, 15, 0.5]],
            ],
            "probability": 0.92,
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.MULTIPLE_ANGLES: ComponentInterfaceExampleValue(
        value={
            "name": "Some angles",
            "type": "Multiple angles",
            "angles": [
                {
                    "name": "First angle",
                    "lines": [
                        [[110, 135, 0.5], [60, 165, 0.5]],
                        [[70, 25, 0.5], [85, 65, 0.5]],
                    ],
                    "probability": 0.82,
                },
                {
                    "name": "Second angle",
                    "lines": [
                        [[130, 210, 0.5], [160, 130, 0.5]],
                        [[140, 40, 0.5], [180, 75, 0.5]],
                    ],
                    "probability": 0.52,
                },
                {
                    "name": "Third angle",
                    "lines": [
                        [[20, 30, 0.5], [20, 100, 0.5]],
                        [[180, 200, 0.5], [210, 200, 0.5]],
                    ],
                    "probability": 0.98,
                },
            ],
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.ELLIPSE: ComponentInterfaceExampleValue(
        value={
            "name": "Some ellipse",
            "type": "Ellipse",
            "major_axis": [[-10, 606, 0.5], [39, 559, 0.5]],
            "minor_axis": [[2, 570, 0.5], [26, 595, 0.5]],
            "probability": 0.92,
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.MULTIPLE_ELLIPSES: ComponentInterfaceExampleValue(
        value={
            "name": "Some ellipse",
            "type": "Multiple ellipses",
            "ellipses": [
                {
                    "major_axis": [[-44, 535, 0.5], [-112, 494, 0.5]],
                    "minor_axis": [[-88, 532, 0.5], [-68, 497, 0.5]],
                    "probability": 0.69,
                },
                {
                    "major_axis": [[-17, 459, 0.5], [-94, 436, 0.5]],
                    "minor_axis": [[-61, 467, 0.5], [-50, 428, 0.5]],
                    "probability": 0.92,
                },
            ],
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.THREE_POINT_ANGLE: ComponentInterfaceExampleValue(
        value={
            "name": "Some 3-point angle",
            "type": "Three-point angle",
            "angle": [[177, 493, 0.5], [22, 489, 0.5], [112, 353, 0.5]],
            "probability": 0.003,
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.MULTIPLE_THREE_POINT_ANGLES: ComponentInterfaceExampleValue(
        value={
            "name": "Multiple 3-point angles",
            "type": "Multiple three-point angles",
            "angles": [
                {
                    "name": "first",
                    "angle": [
                        [300, 237, 0.5],
                        [263, 282, 0.5],
                        [334, 281, 0.5],
                    ],
                    "probability": 0.92,
                },
                {
                    "name": "second",
                    "angle": [
                        [413, 237, 0.5],
                        [35, 160, 0.5],
                        [367, 293, 0.5],
                    ],
                    "probability": 0.69,
                },
            ],
            "version": {"major": 1, "minor": 0},
        },
        extra_info='Optional fields: "name" and "probability"',
    ),
    InterfaceKindChoices.AFFINE_TRANSFORM_REGISTRATION: ComponentInterfaceExampleValue(
        value={
            "3d_affine_transform": [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ]
        },
    ),
    InterfaceKindChoices.CHOICE: ComponentInterfaceExampleValue(
        value="Choice 1",
    ),
    InterfaceKindChoices.MULTIPLE_CHOICE: ComponentInterfaceExampleValue(
        value=["Choice 1", "Choice 2"],
    ),
}

INTERFACE_KIND_TO_ALLOWED_FILE_TYPES = {
    # Can contain:
    # - file extensions (e.g. '.jpg')
    # - subtype MIME type (e.g. 'text/plain')
    # - maintype MIME type (wildcard, e.g. 'text/*')
    # See: https://uppy.io/docs/uppy/#restrictions.
    InterfaceKindChoices.CSV: (
        "application/csv",
        "application/vnd.ms-excel",
        "text/csv",
        "text/plain",
    ),
    InterfaceKindChoices.ZIP: (
        "application/zip",
        "application/x-zip-compressed",
    ),
    InterfaceKindChoices.PDF: ("application/pdf",),
    InterfaceKindChoices.THUMBNAIL_JPG: ("image/jpeg",),
    InterfaceKindChoices.THUMBNAIL_PNG: ("image/png",),
    InterfaceKindChoices.SQREG: (
        "application/octet-stream",
        "application/x-sqlite3",
        "application/vnd.sqlite3",
    ),
    InterfaceKindChoices.MP4: ("video/mp4",),
    InterfaceKindChoices.NEWICK: (
        # MIME types
        "text/x-nh",
        "application/octet-stream",
        # File extensions
        ".newick",
        ".nwk",
        ".tree",
    ),
    InterfaceKindChoices.BIOM: (
        # MIME type
        "application/octet-stream",
        # File extension
        ".biom",
    ),
    InterfaceKindChoices.OBJ: (
        "text/plain",
        "application/octet-stream",
    ),
    **{
        kind: (
            "text/plain",
            "application/json",
        )
        for kind in InterfaceKinds.json
    },
}


INTERFACE_KIND_TO_FILE_EXTENSION = {
    InterfaceKindChoices.CSV: ".csv",
    InterfaceKindChoices.ZIP: ".zip",
    InterfaceKindChoices.PDF: ".pdf",
    InterfaceKindChoices.SQREG: ".sqreg",
    InterfaceKindChoices.THUMBNAIL_JPG: ".jpeg",
    InterfaceKindChoices.THUMBNAIL_PNG: ".png",
    InterfaceKindChoices.OBJ: ".obj",
    InterfaceKindChoices.MP4: ".mp4",
    InterfaceKindChoices.NEWICK: ".newick",
    InterfaceKindChoices.BIOM: ".biom",
    **{kind: ".json" for kind in InterfaceKinds.json},
}

INTERFACE_KIND_TO_CUSTOM_QUEUE = {
    InterfaceKindChoices.NEWICK: acks_late_2xlarge_task.queue,
    InterfaceKindChoices.BIOM: acks_late_2xlarge_task.queue,
}


def component_interface_value_path(instance, filename):
    # Convert the pk to a hex, padded to 4 chars with zeros
    pk_as_padded_hex = f"{instance.pk:04x}"

    return (
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{pk_as_padded_hex[-4:-2]}/{pk_as_padded_hex[-2:]}/{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class ComponentInterfaceValueManager(models.Manager):

    def get_first_or_create(self, **kwargs):
        try:
            return self.get_or_create(**kwargs)
        except MultipleObjectsReturned:
            return self.filter(**kwargs).first(), False


class ComponentInterfaceValue(models.Model, FieldChangeMixin):
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
                    ".obj",
                    ".mp4",
                    ".newick",
                    ".biom",
                )
            ),
            MimeTypeValidator(
                allowed_types=(
                    "application/json",
                    "application/zip",
                    "text/plain",
                    "application/csv",
                    "text/csv",
                    "application/pdf",
                    "image/png",
                    "image/jpeg",
                    "application/octet-stream",
                    "application/x-sqlite3",
                    "application/vnd.sqlite3",
                    "video/mp4",
                )
            ),
        ],
    )
    image = models.ForeignKey(
        to=Image, null=True, blank=True, on_delete=models.PROTECT
    )

    storage_cost_per_year_usd_millicents = deprecate_field(
        models.PositiveIntegerField(
            # We store usd here as the exchange rate regularly changes
            editable=False,
            null=True,
            default=None,
            help_text="The storage cost per year for this image in USD Cents, excluding Tax",
        )
    )
    size_in_storage = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the storage backend",
    )

    _user_upload_validated = False

    objects = ComponentInterfaceValueManager()

    @property
    def title(self):
        if self.interface.super_kind == self.interface.SuperKind.VALUE:
            return str(self.value)
        elif self.interface.super_kind == self.interface.SuperKind.IMAGE:
            try:
                return self.image.name
            except AttributeError:
                return ""
        elif self.interface.super_kind == self.interface.SuperKind.FILE:
            return Path(self.file.name).name
        else:
            logger.error(
                f"Title not implemented for interface super kind: {self.interface.super_kind}"
            )
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

    def __str__(self):
        if self.interface.is_json_kind:
            return f"Component Interface Value {self.pk} for {self.interface}"
        else:
            return self.title

    def save(self, *args, **kwargs):
        if (
            (
                self.initial_value("value")
                not in (None, self.interface.default_value)
                and self.value is not None
                and self.has_changed("value")
            )
            or (self.initial_value("image") and self.has_changed("image"))
            or (self.initial_value("file") and self.has_changed("file"))
        ):
            raise ValidationError(
                "You cannot change the value, file or image of an existing CIV. "
                "Please create a new CIV instead."
            )

        if self.has_changed("file"):
            self.update_size_in_storage()

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        attributes = [
            attribute
            for attribute in [self.value, self.image, self.file.name]
            if attribute is not None
            if attribute != ""
        ]
        if len(attributes) > 1:
            raise ValidationError(
                "Only one of image, value and file can be defined."
            )

        if self.interface.is_image_kind:
            self._validate_image_only()
            self._validate_image_kind()
            if self.interface.kind == InterfaceKindChoices.PANIMG_SEGMENTATION:
                self.interface._validate_voxel_values(self.image)
            if (
                self.interface.kind
                == InterfaceKindChoices.PANIMG_DISPLACEMENT_FIELD
            ):
                self.interface._validate_vector_field(self.image)
        elif self.interface.is_file_kind:
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

    def _validate_image_kind(self):
        if self.interface.is_dicom_image_kind:
            if self.image.dicom_image_set is None:
                raise ValidationError("Image must be DICOM")
        elif self.image.dicom_image_set:
            raise ValidationError("Image may not be DICOM")

    def _validate_file_only(self):
        if not self._user_upload_validated and not self.file:
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
        if self._user_upload_validated:
            return
        if self.interface.store_in_database:
            self._validate_value_only()
            value = self.value
        else:
            self._validate_file_only()
            with self.file.open("r") as f:
                try:
                    value = json.loads(f.read().decode("utf-8"))
                except JSONDecodeError as error:
                    raise ValidationError(error)
                except UnicodeDecodeError:
                    raise ValidationError("The file could not be decoded")
                except MemoryError as error:
                    raise ValidationError(
                        "The file was too large to process, "
                        "please try again with a smaller file"
                    ) from error

        self.interface.validate_against_schema(value=value)

    def validate_user_upload(self, user_upload):
        if not user_upload.is_completed:
            raise ValidationError("User upload is not completed.")
        try:
            if self.interface.is_json_kind:
                try:
                    value = json.loads(user_upload.read_object())
                except JSONDecodeError as error:
                    raise ValidationError(error)
                self.interface.validate_against_schema(value=value)
            elif self.interface.kind == InterfaceKindChoices.NEWICK:
                validate_newick_tree_format(tree=user_upload.read_object())
            elif self.interface.kind == InterfaceKindChoices.BIOM:
                with NamedTemporaryFile() as temp_file:
                    user_upload.download_fileobj(temp_file)
                    validate_biom_format(file=temp_file.name)
        except UnicodeDecodeError:
            raise ValidationError("The file could not be decoded")
        except (
            MemoryError,
            SoftTimeLimitExceeded,
            TimeLimitExceeded,
        ) as error:
            raise ValidationError(
                "The file was too large to process, "
                "please try again with a smaller file"
            ) from error

        self._user_upload_validated = True

    def update_size_in_storage(self):
        if self.file:
            self.size_in_storage = self.file.size
        else:
            raise NotImplementedError

    class Meta:
        ordering = ("pk",)


class ComponentJobManager(models.QuerySet):
    def active(self):
        # We need to use a positive filter here so that the index
        # can be used rather than excluding jobs in final states
        active_choices = (
            c[0]
            for c in ComponentJob.status.field.choices
            if c[0]
            not in [
                ComponentJob.SUCCESS,
                ComponentJob.CANCELLED,
                ComponentJob.FAILURE,
                ComponentJob.CLAIMED,
            ]
        )
        return self.filter(status__in=active_choices)

    def only_completed(self):
        """Jobs that are in their final state"""
        return self.filter(
            status__in=[
                ComponentJob.SUCCESS,
                ComponentJob.CANCELLED,
                ComponentJob.FAILURE,
            ]
        )

    @staticmethod
    def retrieve_existing_civs(*, civ_data):
        """
        Checks if there are existing CIVs for the provided data and returns those.

        Parameters
        ----------
        civ_data
            A list of CIVData objects.

        Returns
        -------
        A list of ComponentInterfaceValues

        """
        existing_civs = []
        for civ in civ_data:
            if (
                civ.user_upload
                or civ.upload_session
                or civ.user_upload_queryset
            ):
                # uploads will create new CIVs, so ignore these
                continue
            elif civ.image:
                try:
                    civs = ComponentInterfaceValue.objects.filter(
                        interface__slug=civ.interface_slug, image=civ.image
                    ).all()
                    existing_civs.extend(civs)
                except ObjectDoesNotExist:
                    continue
            elif civ.file_civ:
                existing_civs.append(civ.file_civ)
            else:
                # values can be of different types, including None and False
                try:
                    civs = ComponentInterfaceValue.objects.filter(
                        interface__slug=civ.interface_slug, value=civ.value
                    ).all()
                    existing_civs.extend(civs)
                except ObjectDoesNotExist:
                    continue

        return existing_civs


class ComponentJob(FieldChangeMixin, UUIDModel):
    # The job statuses come directly from celery.result.AsyncResult.status:
    # http://docs.celeryproject.org/en/latest/reference/celery.result.html
    # Note: check the implementation of active() if changing this to choices
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
    CLAIMED = 12
    VALIDATING_INPUTS = 13

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
        (CLAIMED, "External Execution In Progress"),
        (VALIDATING_INPUTS, "Validating inputs"),
    )

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING, db_index=True
    )
    attempt = models.PositiveSmallIntegerField(editable=False, default=0)
    stdout = models.TextField()
    stderr = models.TextField(default="")
    runtime_metrics = models.JSONField(default=dict, editable=False)
    error_message = models.CharField(max_length=1024, default="")
    detailed_error_message = models.JSONField(blank=True, default=dict)
    input_prefixes = models.JSONField(
        default=dict,
        editable=False,
        help_text=(
            "Map of the ComponentInterfaceValue id to the path prefix to use "
            "for this input, e.g. {'1': 'foo/bar/'} will place CIV 1 at "
            "/input/foo/bar/<relative_path>"
        ),
    )
    signing_key = models.BinaryField(
        max_length=32,
        default=secrets.token_bytes,
        unique=True,
        editable=False,
        help_text="The key used to sign the inference result file",
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
    time_limit = models.PositiveIntegerField(
        help_text="Time limit for the job in seconds",
        validators=[
            MinValueValidator(
                limit_value=settings.COMPONENTS_MINIMUM_JOB_DURATION
            ),
            MaxValueValidator(
                limit_value=settings.COMPONENTS_MAXIMUM_JOB_DURATION
            ),
        ],
    )
    requires_gpu_type = models.CharField(
        editable=False,
        max_length=4,
        choices=GPUTypeChoices.choices,
        help_text="What GPU is required by this job?",
    )
    requires_memory_gb = models.PositiveSmallIntegerField(
        editable=False,
        help_text="How much main memory (DRAM) is required by this job?",
    )
    use_warm_pool = models.BooleanField(
        default=False, editable=False, help_text="Whether to use warm pools"
    )

    inputs = models.ManyToManyField(
        to=ComponentInterfaceValue,
        related_name="%(app_label)s_%(class)ss_as_input",
    )
    outputs = models.ManyToManyField(
        to=ComponentInterfaceValue,
        related_name="%(app_label)s_%(class)ss_as_output",
    )

    objects = ComponentJobManager.as_manager()

    @property
    def status_url(self) -> str:
        raise NotImplementedError

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if not adding:
            for field in (
                "requires_gpu_type",
                "requires_memory_gb",
                "time_limit",
                "signing_key",
            ):
                if self.has_changed(field):
                    raise ValueError(f"{field} cannot be changed")

        super().save()

        if adding:
            self.create_utilization()

    def update_status(
        self,
        *,
        status: STATUS_CHOICES,
        stdout: str = "",
        stderr: str = "",
        error_message="",
        detailed_error_message=None,
        duration=None,
        compute_cost_euro_millicents=None,
        runtime_metrics=None,
    ):
        self.status = status

        if stdout:
            self.stdout = stdout

        if stderr:
            self.stderr = stderr

        if error_message:
            self.error_message = error_message[:1024]

        if detailed_error_message:
            self.detailed_error_message = {
                str(key): value
                for key, value in detailed_error_message.items()
            }

        if duration is not None:
            self.utilization.duration = duration
            self.utilization.save(update_fields=["duration"])

        if compute_cost_euro_millicents is not None:
            self.utilization.compute_cost_euro_millicents = (
                compute_cost_euro_millicents
            )
            self.utilization.save(
                update_fields=["compute_cost_euro_millicents"]
            )

        if runtime_metrics is not None:
            self.runtime_metrics = runtime_metrics

        self.save()

        if self.status == self.SUCCESS:
            on_commit(self.execute_task_on_success)
        elif self.status in [self.FAILURE, self.CANCELLED]:
            on_commit(self.execute_task_on_failure)

    @property
    def executor_kwargs(self):
        return {
            "job_id": f"{self._meta.app_label}-{self._meta.model_name}-{self.pk}-{self.attempt:02}",
            "exec_image_repo_tag": self.container.shimmed_repo_tag,
            "time_limit": self.time_limit,
            "requires_gpu_type": self.requires_gpu_type,
            "memory_limit": self.requires_memory_gb,
            "use_warm_pool": self.use_warm_pool,
            "signing_key": self.signing_key,
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

    @cached_property
    def inputs_complete(self):
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
            self.VALIDATING_INPUTS,
        }

    @property
    def finished(self):
        return self.status in {
            self.FAILURE,
            self.SUCCESS,
            self.CANCELLED,
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
            self.VALIDATING_INPUTS,
        }:
            return "info"
        else:
            return "secondary"

    @property
    def runtime_metrics_chart(self):
        instance_metrics = self.runtime_metrics["instance"]
        n_cpu = instance_metrics["cpu"]

        if instance_metrics["gpus"]:
            gpu_str = (
                f"{instance_metrics['gpus']}x {instance_metrics['gpu_type']}"
            )
        else:
            gpu_str = "No"

        title = f"{instance_metrics['name']} / {instance_metrics['cpu']} CPU / {instance_metrics['memory']} GB Memory / {gpu_str} GPU"

        return components_line(
            values=[
                {
                    "Metric": metric["label"],
                    "Timestamp": timestamp,
                    "Percent": (
                        value / (n_cpu * 100.0)
                        if metric["label"] == "CPUUtilization"
                        else value / 100.0
                    ),
                }
                for metric in self.runtime_metrics["metrics"]
                for timestamp, value in zip(
                    metric["timestamps"], metric["values"], strict=True
                )
            ],
            title=title,
            single_thread_limit=100.0 / n_cpu,
            tooltip=[
                {
                    "field": metric["label"],
                    "type": "quantitative",
                    "format": ".2%",
                }
                for metric in self.runtime_metrics["metrics"]
            ],
        )

    def create_utilization(self):
        raise NotImplementedError

    @property
    def utilization(self):
        raise NotImplementedError

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["status", "created"]),
        ]


def docker_image_path(instance, filename):
    return (
        f"docker/"
        f"images/"
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class ImportStatusChoices(IntegerChoices):
    INITIALIZED = 0, "Initialized"
    QUEUED = 1, "Queued"
    RETRY = 2, "Re-Queued"
    STARTED = 3, "Started"
    CANCELLED = 4, "Cancelled"
    FAILED = 5, "Failed"
    COMPLETED = 6, "Completed"


class ComponentImageManager(models.Manager):
    def executable_images(self):
        return self.filter(
            is_manifest_valid=True, is_in_registry=True, is_removed=False
        )

    def active_images(self):
        return self.executable_images().filter(is_desired_version=True)


class ComponentImage(FieldChangeMixin, models.Model):
    SHIM_IMAGE = True

    ImportStatusChoices = ImportStatusChoices
    GPUTypeChoices = GPUTypeChoices

    objects = ComponentImageManager()

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    user_upload = models.ForeignKey(
        UserUpload, blank=True, null=True, on_delete=models.SET_NULL
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
            ".tar.gz archive of the container image produced from the command "
            "'docker save IMAGE | gzip -c > IMAGE.tar.gz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
        storage=private_s3_storage,
    )
    image_sha256 = models.CharField(editable=False, max_length=71)
    latest_shimmed_version = models.CharField(
        editable=False, max_length=8, default=""
    )

    import_status = models.PositiveSmallIntegerField(
        choices=ImportStatusChoices.choices,
        default=ImportStatusChoices.INITIALIZED,
        db_index=True,
    )
    is_manifest_valid = models.BooleanField(
        default=None,
        null=True,
        editable=False,
        help_text="Is this image's manifest valid?",
    )
    is_in_registry = models.BooleanField(
        default=False,
        editable=False,
        help_text="Is this image in the container registry?",
    )
    is_removed = models.BooleanField(
        default=False,
        editable=False,
        help_text=(
            "If this image has been removed then it has been "
            "removed from storage and cannot be activated"
        ),
    )
    status = models.TextField(editable=False)

    storage_cost_per_year_usd_millicents = deprecate_field(
        models.PositiveIntegerField(
            # We store usd here as the exchange rate regularly changes
            editable=False,
            null=True,
            default=None,
            help_text="The storage cost per year for this image in USD Cents, excluding Tax",
        )
    )

    size_in_storage = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the storage backend",
    )
    size_in_registry = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the registry",
    )

    comment = models.TextField(
        blank=True,
        default="",
        help_text="Add any information (e.g. version ID) about this image here.",
    )
    is_desired_version = models.BooleanField(default=False, editable=False)

    def get_absolute_url(self):
        raise NotImplementedError

    @property
    def import_status_url(self) -> str:
        raise NotImplementedError

    def __str__(self):
        out = f"{self._meta.verbose_name.title()} {self.pk_display} (SHA256: {self.sha256_display}"

        if self.comment:
            out += f", comment: {truncatewords(self.comment, 4)}"

        out += ")"

        return out

    @cached_property
    def can_execute(self):
        return (
            self.__class__.objects.executable_images()
            .filter(pk=self.pk)
            .exists()
        )

    @property
    def linked_file(self):
        return self.image

    @property
    def sha256_display(self):
        if self.image_sha256:
            return self.image_sha256.split(":")[1][:8]
        else:
            return "Unknown"

    @property
    def pk_display(self):
        return str(self.pk).split("-")[0]

    def clear_can_execute_cache(self):
        try:
            del self.can_execute
        except AttributeError:
            pass

    def save(self, *args, **kwargs):
        if self.is_removed and self.image:
            raise RuntimeError("Image cannot be set when removed")

        if (
            not self.is_removed
            and self.initial_value("image")
            and self.has_changed("image")
        ):
            raise RuntimeError("The image cannot be changed")

        image_needs_validation = (
            self.image
            and self.import_status == ImportStatusChoices.INITIALIZED
            and self.is_manifest_valid is None
        )

        if image_needs_validation:
            self.import_status = ImportStatusChoices.QUEUED
            validate_image_now = True
        else:
            validate_image_now = False

        if self.has_changed("image") or self.has_changed("is_in_registry"):
            self.update_size_in_storage()

        super().save(*args, **kwargs)

        if validate_image_now:
            on_commit(
                validate_docker_image.signature(
                    kwargs={
                        "app_label": self._meta.app_label,
                        "model_name": self._meta.model_name,
                        "pk": self.pk,
                        "mark_as_desired": True,
                    },
                    immutable=True,
                ).apply_async
            )

    def assign_docker_image_from_upload(self):
        on_commit(
            assign_docker_image_from_upload.signature(
                kwargs={
                    "app_label": self._meta.app_label,
                    "model_name": self._meta.model_name,
                    "pk": self.pk,
                }
            ).apply_async
        )

    def get_peer_images(self):
        raise NotImplementedError

    @transaction.atomic
    def mark_desired_version(self):
        self.clear_can_execute_cache()
        if self.is_manifest_valid and self.can_execute:
            images = self.get_peer_images()

            for image in images:
                if image == self:
                    image.is_desired_version = True
                else:
                    image.is_desired_version = False

            self.__class__.objects.bulk_update(images, ["is_desired_version"])

        else:
            raise RuntimeError(
                "Tried to mark invalid image as desired version."
            )

    @property
    def original_repo_tag(self):
        """The tag of this image in the container repository"""
        return (
            f"{settings.COMPONENTS_REGISTRY_URL}/"
            f"{settings.COMPONENTS_REGISTRY_PREFIX}/"
            f"{self._meta.app_label}/{self._meta.model_name}:{self.pk}"
        )

    @property
    def shimmed_repo_tag(self):
        return f"{self.original_repo_tag}-{self.latest_shimmed_version}"

    class Meta:
        abstract = True

    @property
    def animate(self):
        return self.import_status == self.ImportStatusChoices.STARTED

    @property
    def finished(self):
        return self.import_status in {
            self.ImportStatusChoices.FAILED,
            self.ImportStatusChoices.COMPLETED,
            self.ImportStatusChoices.CANCELLED,
        }

    @property
    def import_status_context(self):
        if self.import_status == self.ImportStatusChoices.COMPLETED:
            return "success"
        elif self.import_status in {
            self.ImportStatusChoices.FAILED,
            self.ImportStatusChoices.CANCELLED,
        }:
            return "danger"
        elif self.import_status in {
            self.ImportStatusChoices.INITIALIZED,
            self.ImportStatusChoices.QUEUED,
            self.ImportStatusChoices.RETRY,
            self.ImportStatusChoices.STARTED,
        }:
            return "info"
        else:
            return "secondary"

    def calculate_size_in_registry(self):
        if self.is_in_registry:
            command = _repo_login_and_run(
                command=["crane", "manifest", self.original_repo_tag]
            )
            manifest = json.loads(command.stdout)
            return (
                sum(layer["size"] for layer in manifest["layers"])
                + manifest["config"]["size"]
            )
        else:
            return 0

    def update_size_in_storage(self):
        if not self.image:
            self.size_in_storage = 0
            self.size_in_registry = 0
        else:
            self.size_in_storage = self.image.size
            self.size_in_registry = self.calculate_size_in_registry()


class CIVData:

    @property
    def interface_slug(self):
        return self._interface_slug

    @property
    def value(self):
        return self._json_value

    @property
    def image(self):
        return self._image

    @property
    def upload_session(self):
        return self._upload_session

    @property
    def user_upload(self):
        return self._user_upload

    @property
    def user_upload_queryset(self):
        return self._user_upload_queryset

    @property
    def file_civ(self):
        return self._file_civ

    @property
    def dicom_upload_with_name(self):
        return self._dicom_upload_with_name

    def __init__(self, *, interface_slug, value):
        self._interface_slug = interface_slug
        self._initial_value = value
        self._json_value = None
        self._image = None
        self._upload_session = None
        self._user_upload = None
        self._user_upload_queryset = None
        self._file_civ = None
        self._dicom_upload_with_name = None

        ci = ComponentInterface.objects.get(slug=interface_slug)

        if ci.super_kind == ci.SuperKind.VALUE:
            self._init_json_civ_data()
        elif ci.super_kind == ci.SuperKind.IMAGE:
            self._init_image_civ_data()
        elif ci.super_kind == ci.SuperKind.FILE:
            self._init_file_civ_data()
        else:
            raise NotImplementedError(
                f"Unknown interface super kind: {ci.super_kind}"
            )

        self.validate()

    def _init_json_civ_data(self):
        if isinstance(
            self._initial_value,
            (str | bool | int | float | dict | list | None),
        ):
            self._json_value = self._initial_value
        else:
            raise ValidationError(
                f"Unknown data type {type(self._initial_value)} for interface {self._interface_slug}"
            )

    def _init_image_civ_data(self):
        from grandchallenge.cases.widgets import DICOMUploadWithName

        if isinstance(self._initial_value, DICOMUploadWithName):
            self._dicom_upload_with_name = self._initial_value
        elif isinstance(self._initial_value, QuerySet):
            self._user_upload_queryset = self._initial_value
        elif isinstance(self._initial_value, RawImageUploadSession):
            self._upload_session = self._initial_value
        elif isinstance(self._initial_value, Image):
            self._image = self._initial_value
        elif self._initial_value is None:
            self._image = None
        else:
            raise ValidationError(
                f"Unknown data type {type(self._initial_value)} for interface {self._interface_slug}"
            )

    def _init_file_civ_data(self):
        if isinstance(self._initial_value, UserUpload):
            self._user_upload = self._initial_value
        elif isinstance(self._initial_value, ComponentInterfaceValue):
            self._file_civ = self._initial_value
        elif self._initial_value is None:
            self._file_civ = None
        else:
            raise ValidationError(
                f"Unknown data type {type(self._initial_value)} for interface {self._interface_slug}"
            )

    def validate(self):
        unique_properties = [
            self.value,
            self.image,
            self.user_upload,
            self.upload_session,
            self.user_upload_queryset,
            self.dicom_upload_with_name,
            self.file_civ,
        ]

        # Ensure at most one of these properties is set
        # None can be an acceptable value, so 0 is ok
        if sum(bool(prop) for prop in unique_properties) > 1:
            raise ValidationError(
                "Only one of value, image, user_upload, upload_session, "
                "user_upload_queryset, dicom_upload_with_name or file_civ "
                "can be provided for a single CIVData object."
            )


class CIVSetStringRepresentationMixin:
    def __str__(self):
        result = [str(self.pk)]

        if self.title:
            result.append(f"{self.title!r}")

        result.append(self.__content_str)
        return ", ".join(result)

    @property
    def __content_str(self):
        civs = self.values.all()
        nr = len(civs)
        if nr == 0:
            return "No content"

        if nr > 5:
            return "5+ items"

        content = [f"{civ.interface.title}: {civ.title[:30]}" for civ in civs]
        return ", ".join(content)


class CIVSetObjectPermissionsMixin:
    @property
    def view_perm(self):
        return f"view_{self._meta.model_name}"

    @property
    def change_perm(self):
        return f"change_{self._meta.model_name}"

    @property
    def delete_perm(self):
        return f"delete_{self._meta.model_name}"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        raise NotImplementedError


class CIVForObjectMixin:

    def add_civ(self, *, civ):
        if not self.is_editable:
            raise CIVNotEditableException(f"{self} is not editable.")

    def remove_civ(self, *, civ):
        if not self.is_editable:
            raise CIVNotEditableException(f"{self} is not editable.")

    def validate_values_and_execute_linked_task(
        self, *, values, user, linked_task=None
    ):
        for civ_data in values:
            self.create_civ(
                civ_data=civ_data,
                user=user,
                linked_task=linked_task,
            )

    def create_civ(self, *, civ_data, user=None, linked_task=None):
        if not self.is_editable:
            raise CIVNotEditableException(
                f"{self} is not editable. CIVs cannot be added or removed from it.",
            )

        try:
            if (
                civ_data.interface_slug
                not in self.base_object.allowed_socket_slugs
            ):
                raise CINotAllowedException(
                    f"Socket {civ_data.interface_slug!r} is not allowed "
                    f"for this {self.base_object._meta.model_name}."
                )
        except AttributeError:
            pass

        ci = ComponentInterface.objects.get(slug=civ_data.interface_slug)
        current_civ = self.get_current_value_for_interface(
            interface=ci, user=user
        )

        if ci.super_kind == ci.SuperKind.VALUE:
            return self._create_civ_for_value(
                ci=ci,
                current_civ=current_civ,
                new_value=civ_data.value,
                user=user,
                linked_task=linked_task,
            )
        elif ci.super_kind == ci.SuperKind.IMAGE:
            return self._create_civ_for_image(
                ci=ci,
                current_civ=current_civ,
                user=user,
                image=civ_data.image,
                upload_session=civ_data.upload_session,
                user_upload_queryset=civ_data.user_upload_queryset,
                dicom_upload_with_name=civ_data.dicom_upload_with_name,
                linked_task=linked_task,
            )
        elif ci.super_kind == ci.SuperKind.FILE:
            return self._create_civ_for_file(
                ci=ci,
                current_civ=current_civ,
                file_civ=civ_data.file_civ,
                user_upload=civ_data.user_upload,
                linked_task=linked_task,
            )
        else:
            raise NotImplementedError(
                f"Unknown interface super kind: {ci.super_kind}"
            )

    def _create_civ_for_value(
        self, *, ci, current_civ, new_value, user, linked_task=None
    ):
        current_value = current_civ.value if current_civ else None

        civ, created = ComponentInterfaceValue.objects.get_first_or_create(
            interface=ci, value=new_value
        )

        if current_value != new_value or (
            current_value in ci.default_field.empty_values
            and new_value in ci.default_field.empty_values
        ):
            try:
                civ.full_clean()
                civ.save()
                self.add_civ(civ=civ)
                self.remove_civ(civ=current_civ)
            except ValidationError as e:
                if created:
                    civ.delete()

                if new_value in ci.default_field.empty_values:
                    self.remove_civ(civ=current_civ)
                else:
                    error_handler = self.get_error_handler()
                    error_handler.handle_error(
                        interface=ci,
                        error_message=format_validation_error_message(error=e),
                        user=user,
                    )
                    return

            if linked_task is not None:
                on_commit(signature(linked_task).apply_async)

    def _create_civ_for_image(  # noqa: C901
        self,
        *,
        ci,
        current_civ,
        user=None,
        image=None,
        upload_session=None,
        user_upload_queryset=None,
        dicom_upload_with_name=None,
        linked_task=None,
    ):
        current_image = current_civ.image if current_civ else None

        if image:
            if current_image == image:
                # Nothing to do.
                return
            civ, created = ComponentInterfaceValue.objects.get_first_or_create(
                interface=ci, image=image
            )

            if created:
                try:
                    civ.full_clean()
                except ValidationError as e:
                    civ.delete()
                    error_handler = self.get_error_handler()
                    error_handler.handle_error(
                        interface=ci,
                        error_message=format_validation_error_message(error=e),
                        user=user,
                    )
                    return

            self.remove_civ(civ=current_civ)
            self.add_civ(civ=civ)

            if linked_task is not None:
                on_commit(signature(linked_task).apply_async)

        elif upload_session or user_upload_queryset:
            # Local import to avoid circular dependency
            from grandchallenge.components.tasks import add_image_to_object

            if user_upload_queryset:
                if not user:
                    raise RuntimeError(
                        f"You need to provide a user along with the user upload "
                        f"queryset for interface {ci}"
                    )
                upload_session = RawImageUploadSession.objects.create(
                    creator=user
                )
                upload_session.user_uploads.set(user_upload_queryset)

            upload_session.process_images(
                linked_app_label=self._meta.app_label,
                linked_model_name=self._meta.model_name,
                linked_object_pk=self.pk,
                linked_interface_slug=ci.slug,
                linked_task=add_image_to_object.signature(
                    kwargs={
                        "app_label": self._meta.app_label,
                        "model_name": self._meta.model_name,
                        "object_pk": self.pk,
                        "interface_pk": str(ci.pk),
                        "linked_task": linked_task,
                    },
                    immutable=True,
                ),
            )
        elif dicom_upload_with_name:
            from grandchallenge.cases.tasks import (
                import_dicom_to_health_imaging,
            )
            from grandchallenge.components.tasks import add_image_to_object

            if not user:
                raise RuntimeError(
                    f"You need to provide a user along with the user upload "
                    f"queryset for interface {ci}"
                )
            upload = DICOMImageSetUpload(
                creator=user, name=dicom_upload_with_name.name
            )
            upload.task_on_success = add_image_to_object.signature(
                kwargs={
                    "app_label": self._meta.app_label,
                    "model_name": self._meta.model_name,
                    "object_pk": self.pk,
                    "interface_pk": str(ci.pk),
                    "dicom_image_set_upload_pk": upload.pk,
                    "linked_task": linked_task,
                },
                immutable=True,
            )
            upload.full_clean()
            upload.save()
            upload.user_uploads.set(dicom_upload_with_name.user_uploads)

            on_commit(
                import_dicom_to_health_imaging.signature(
                    kwargs={"dicom_imageset_upload_pk": upload.pk}
                ).apply_async
            )
        else:
            raise NotImplementedError

    def _create_civ_for_file(
        self,
        *,
        ci,
        current_civ,
        file_civ=None,
        user_upload=None,
        linked_task=None,
    ):
        if file_civ:
            self.remove_civ(civ=current_civ)
            self.add_civ(civ=file_civ)

            if linked_task is not None:
                on_commit(signature(linked_task).apply_async)

        elif user_upload:
            from grandchallenge.components.tasks import add_file_to_object

            custom_queue = INTERFACE_KIND_TO_CUSTOM_QUEUE.get(ci.kind, False)
            task_queue_kwarg = {}
            if custom_queue:
                task_queue_kwarg["queue"] = custom_queue

            transaction.on_commit(
                add_file_to_object.signature(
                    kwargs={
                        "app_label": self._meta.app_label,
                        "model_name": self._meta.model_name,
                        "user_upload_pk": str(user_upload.pk),
                        "interface_pk": str(ci.pk),
                        "object_pk": self.pk,
                        "linked_task": linked_task,
                    },
                    **task_queue_kwarg,
                ).apply_async
            )

        else:
            # if no new value is provided (user selects '---' in dropdown)
            # delete old CIV
            self.remove_civ(civ=current_civ)

    def get_civ_for_interface(self, interface):
        raise NotImplementedError

    def get_current_value_for_interface(self, *, interface, user):
        try:
            return self.get_civ_for_interface(interface=interface)
        except ObjectDoesNotExist:
            return None
        except MultipleObjectsReturned as e:
            error_handler = self.get_error_handler()
            error_handler.handle_error(
                interface=interface,
                error_message="An unexpected error occurred",
                user=user,
            )
            raise e

    def get_error_handler(self, *, linked_object=None):
        # local imports to prevent circular dependency
        from grandchallenge.algorithms.models import Job
        from grandchallenge.archives.models import ArchiveItem
        from grandchallenge.evaluation.models import Evaluation
        from grandchallenge.reader_studies.models import DisplaySet

        if isinstance(linked_object, RawImageUploadSession):
            return RawImageUploadSessionErrorHandler(
                upload_session=linked_object,
                linked_object=self,
            )
        elif isinstance(linked_object, DICOMImageSetUpload):
            return DICOMImageSetUploadErrorHandler(
                dicom_image_set_upload=linked_object,
                linked_object=self,
            )
        elif isinstance(self, Job):
            return JobCIVErrorHandler(job=self)
        elif isinstance(self, Evaluation):
            return EvaluationCIVErrorHandler(job=self)
        elif linked_object and isinstance(linked_object, UserUpload):
            return UserUploadCIVErrorHandler(
                user_upload=linked_object,
            )
        elif isinstance(self, (ArchiveItem, DisplaySet)) and not linked_object:
            return FallbackCIVValidationErrorHandler()
        else:
            raise RuntimeError("No appropriate error handler found.")


class LinkedComponentInterfacesMixin:

    @property
    def civ_sets_related_manager(self):
        raise NotImplementedError

    @cached_property
    def linked_component_interfaces(self):
        return ComponentInterface.objects.filter(
            pk__in=self.civ_sets_related_manager.exclude(
                values__isnull=True
            ).values_list("values__interface__pk", flat=True)
        ).distinct()


class Tarball(UUIDModel):
    ImportStatusChoices = ImportStatusChoices

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    import_status = models.PositiveSmallIntegerField(
        choices=ImportStatusChoices.choices,
        default=ImportStatusChoices.INITIALIZED,
        db_index=True,
    )
    status = models.TextField(editable=False)
    user_upload = models.ForeignKey(
        UserUpload,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        validators=[validate_gzip_mimetype],
    )
    sha256 = models.CharField(editable=False, max_length=71)
    size_in_storage = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the storage backend",
    )
    comment = models.TextField(
        blank=True,
        default="",
        help_text="Add any information (e.g. version ID) about this object here.",
    )
    is_desired_version = models.BooleanField(default=False, editable=False)

    class Meta:
        abstract = True
        ordering = ("created",)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        raise NotImplementedError

    def get_absolute_url(self):
        raise NotImplementedError

    @property
    def import_status_url(self) -> str:
        raise NotImplementedError

    def get_peer_tarballs(self):
        raise NotImplementedError

    @property
    def linked_file(self):
        raise NotImplementedError

    @transaction.atomic
    def mark_desired_version(self, peer_tarballs=None):
        peer_tarballs = list(peer_tarballs or self.get_peer_tarballs())
        for tb in peer_tarballs:
            tb.is_desired_version = False
        self.is_desired_version = True
        peer_tarballs.append(self)
        self.__class__.objects.bulk_update(
            peer_tarballs, ["is_desired_version"]
        )

    @property
    def import_status_context(self):
        if self.import_status == ImportStatusChoices.COMPLETED:
            return "success"
        elif self.import_status in {
            ImportStatusChoices.FAILED,
            ImportStatusChoices.CANCELLED,
        }:
            return "danger"
        else:
            return "info"

    @property
    def animate(self):
        return self.import_status == ImportStatusChoices.INITIALIZED

    @property
    def finished(self):
        return self.import_status in {
            self.ImportStatusChoices.FAILED,
            self.ImportStatusChoices.COMPLETED,
            self.ImportStatusChoices.CANCELLED,
        }
