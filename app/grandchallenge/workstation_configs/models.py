from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.validators import JSONValidator
from grandchallenge.subdomains.utils import reverse

OVERLAY_SEGMENTS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-06/schema",
    "$id": "http://example.com/example.json",
    "type": "array",
    "title": "The Overlay Segments Schema",
    "description": "Define the overlay segments for the LUT.",
    "items": {
        "$id": "#/items",
        "type": "object",
        "title": "The Segment Schema",
        "description": "Defines what each segment of the LUT represents.",
        "default": {},
        "examples": [
            {
                "name": "Metastasis",
                "voxel_value": 1,
                "visible": True,
                "metric_template": "{{metrics.volumes[0]}} mm³",
            }
        ],
        "required": ["voxel_value", "name", "visible"],
        "additionalProperties": False,
        "properties": {
            "voxel_value": {
                "$id": "#/items/properties/voxel_value",
                "type": "integer",
                "title": "The Voxel Value Schema",
                "description": "The value of the LUT for this segment.",
                "default": 0,
                "examples": [1],
            },
            "name": {
                "$id": "#/items/properties/name",
                "type": "string",
                "title": "The Name Schema",
                "description": "What this segment should be called.",
                "default": "",
                "examples": ["Metastasis"],
            },
            "visible": {
                "$id": "#/items/properties/visible",
                "type": "boolean",
                "title": "The Visible Schema",
                "description": "Whether this segment is visible by default.",
                "default": True,
                "examples": [True],
            },
            "metric_template": {
                "$id": "#/items/properties/metric_template",
                "type": "string",
                "title": "The Metric Template Schema",
                "description": "The jinja template to determine which property from the results.json should be used as the label text.",
                "default": "",
                "examples": ["{{metrics.volumes[0]}} mm³"],
            },
        },
    },
}

KEY_BINDINGS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-06/schema",
    "$id": "http://example.com/example.json",
    "type": "array",
    "title": "The Key Bindings Schema",
    "description": "Define the key bindings for the workstation.",
    "items": {
        "$id": "#/items",
        "type": "object",
        "title": "The Key Binding Schema",
        "description": "Defines a key binding for a command.",
        "default": {},
        "examples": [
            {
                "key": "ctrl+shift+k",
                "command": "editor.action.deleteLines",
                "when": "editorTextFocus",
            }
        ],
        "required": ["key", "command"],
        "additionalProperties": False,
        "properties": {
            "key": {
                "$id": "#/items/properties/key",
                "type": "string",
                "title": "The Key Schema",
                "description": "The keys used for this binding.",
                "default": "",
                "examples": ["ctrl+shift+k"],
            },
            "command": {
                "$id": "#/items/properties/command",
                "type": "string",
                "title": "The Command Schema",
                "description": "The command called by this binding.",
                "default": "",
                "examples": ["editor.action.deleteLines"],
            },
            "when": {
                "$id": "#/items/properties/when",
                "type": "string",
                "title": "The When Schema",
                "description": "The condition that must be met for this command to be called.",
                "default": "",
                "examples": ["editorTextFocus"],
            },
        },
    },
}


class WorkstationConfig(TitleSlugDescriptionModel, UUIDModel):
    class Orientation(models.TextChoices):
        AXIAL = "A", "Axial"
        CORONAL = "C", "Coronal"
        SAGITTAL = "S", "Sagittal"

    class SlabRenderMethod(models.TextChoices):
        MAXIMUM = "MAX", "Maximum"
        MINIMUM = "MIN", "Minimum"
        AVERAGE = "AVG", "Average"

    class ImageContext(models.TextChoices):
        PATHOLOGY = "PATH", "Pathology"
        OPHTHALMOLOGY = "OPHTH", "Ophthalmology"
        MPMRI = "MPMRI", "Multiparametric MRI"

    class ImageInterpolationType(models.TextChoices):
        NEAREST = "NN", "NearestNeighbor"
        TRILINEAR = "TL", "Trilinear"

    creator = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.SET_NULL
    )

    window_presets = models.ManyToManyField(
        to="WindowPreset",
        blank=True,
        related_name="workstation_window_presets",
    )

    default_window_preset = models.ForeignKey(
        to="WindowPreset",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="workstation_default_window_presets",
    )

    image_context = models.CharField(
        blank=True, max_length=6, choices=ImageContext.choices
    )

    # 4 digits, 2 decimal places, 0.01 min, 99.99 max
    default_slab_thickness_mm = models.DecimalField(
        blank=True,
        null=True,
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(limit_value=0.01)],
    )

    default_slab_render_method = models.CharField(
        max_length=3, choices=SlabRenderMethod.choices, blank=True
    )

    default_orientation = models.CharField(
        max_length=1, choices=Orientation.choices, blank=True
    )

    overlay_luts = models.ManyToManyField(
        to="LookUpTable", blank=True, related_name="workstation_overlay_luts"
    )

    default_overlay_lut = models.ForeignKey(
        to="LookUpTable", blank=True, null=True, on_delete=models.SET_NULL
    )

    default_overlay_interpolation = models.CharField(
        max_length=2,
        choices=ImageInterpolationType.choices,
        default=ImageInterpolationType.NEAREST,
        blank=True,
    )

    # 3 digits, 2 decimal places, 0.00 min, 1.00 max
    default_overlay_alpha = models.DecimalField(
        blank=True,
        null=True,
        max_digits=3,
        decimal_places=2,
        validators=[
            MinValueValidator(limit_value=0.00),
            MaxValueValidator(limit_value=1.00),
        ],
    )

    overlay_segments = models.JSONField(
        default=list,
        blank=True,
        validators=[JSONValidator(schema=OVERLAY_SEGMENTS_SCHEMA)],
    )

    key_bindings = models.JSONField(
        default=list,
        blank=True,
        validators=[JSONValidator(schema=KEY_BINDINGS_SCHEMA)],
    )

    # 4 digits, 2 decimal places, 0.01 min, 99.99 max
    default_zoom_scale = models.DecimalField(
        blank=True,
        null=True,
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(limit_value=0.01)],
    )

    show_image_info_plugin = models.BooleanField(default=True)
    show_display_plugin = models.BooleanField(default=True)
    show_image_switcher_plugin = models.BooleanField(default=True)
    show_algorithm_output_plugin = models.BooleanField(
        default=True,
        help_text="Show algorithm outputs with navigation controls",
    )
    show_overlay_plugin = models.BooleanField(default=True)
    show_invert_tool = models.BooleanField(default=True)
    show_flip_tool = models.BooleanField(default=True)
    show_window_level_tool = models.BooleanField(default=True)
    show_reset_tool = models.BooleanField(default=True)
    show_overlay_selection_tool = models.BooleanField(default=True)
    show_lut_selection_tool = models.BooleanField(default=True)

    enable_contrast_enhancement = models.BooleanField(
        default=False,
        verbose_name="Enable contrast enhancement preprocessing (fundus)",
    )
    auto_jump_center_of_gravity = models.BooleanField(
        default=True,
        help_text="Jump to center of gravity of first output when viewing algorithm "
        "results or the first overlay segment when viewing a reader study",
    )

    class Meta(TitleSlugDescriptionModel.Meta, UUIDModel.Meta):
        ordering = ("created", "creator")

    def __str__(self):
        return f"{self.title} (created by {self.creator})"

    def get_absolute_url(self):
        return reverse(
            "workstation-configs:detail", kwargs={"slug": self.slug}
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.creator:
            assign_perm(
                f"{self._meta.app_label}.change_{self._meta.model_name}",
                self.creator,
                self,
            )


class WindowPreset(TitleSlugDescriptionModel):
    width = models.PositiveIntegerField(
        blank=True, null=True, validators=[MinValueValidator(limit_value=1)]
    )
    center = models.IntegerField(blank=True, null=True)

    lower_percentile = models.PositiveSmallIntegerField(
        blank=True, null=True, validators=[MaxValueValidator(limit_value=100)]
    )

    upper_percentile = models.PositiveSmallIntegerField(
        blank=True, null=True, validators=[MaxValueValidator(limit_value=100)]
    )

    def _validate_percentile(self):
        if self.upper_percentile <= self.lower_percentile:
            raise ValidationError(
                f"Upper percentile ({self.upper_percentile}%) should be below the "
                f"lower percentile ({self.lower_percentile}%)"
            )

    def _validate_fixed(self):
        pass

    def clean(self):
        super().clean()
        window_center_all = None not in {self.width, self.center}
        window_center_none = all(v is None for v in {self.width, self.center})
        percentile_all = None not in {
            self.lower_percentile,
            self.upper_percentile,
        }
        percentile_none = all(
            v is None for v in {self.lower_percentile, self.upper_percentile}
        )

        if window_center_all and percentile_none:
            self._validate_fixed()
        elif percentile_all and window_center_none:
            self._validate_percentile()
        else:
            raise ValidationError(
                "Either (upper and lower percentiles) or (width and center) should be entered"
            )

    class Meta(TitleSlugDescriptionModel.Meta):
        ordering = ("title",)
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_either_fixed_or_percentile",
                check=(
                    models.Q(
                        center__isnull=False,
                        width__isnull=False,
                        lower_percentile__isnull=True,
                        upper_percentile__isnull=True,
                    )
                    | models.Q(
                        center__isnull=True,
                        width__isnull=True,
                        lower_percentile__isnull=False,
                        upper_percentile__isnull=False,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_upper_gt_lower_percentile",
                check=models.Q(
                    upper_percentile__gt=models.F("lower_percentile")
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_width_gt_0",
                check=models.Q(width__gt=0) | models.Q(width__isnull=True),
            ),
        ]

    def __str__(self):
        if None not in {self.center, self.width}:
            return f"{self.title} (center {self.center}, width {self.width})"
        else:
            return f"{self.title} ({self.lower_percentile}%-{self.upper_percentile}%)"


class LookUpTable(TitleSlugDescriptionModel):

    COLOR_INTERPOLATION_RGB = "RGB"
    COLOR_INTERPOLATION_HLS = "HLS"
    COLOR_INTERPOLATION_HLS_POS = "HLSpos"
    COLOR_INTERPOLATION_HLS_NEG = "HLSneg"
    COLOR_INTERPOLATION_CONSTANT = "Constant"
    COLOR_INTERPOLATION_CHOICES = (
        (COLOR_INTERPOLATION_RGB, "RGB"),
        (COLOR_INTERPOLATION_HLS, "HLS"),
        (COLOR_INTERPOLATION_HLS_POS, "HLS Positive"),
        (COLOR_INTERPOLATION_HLS_NEG, "HLS Negative"),
        (COLOR_INTERPOLATION_CONSTANT, "Constant"),
    )

    # These regex reflect what MeVisLab accepts as color and alpha strings
    # and kept for compatibility. Probably, we want to clean these fields up
    # later for use elsewhere.
    COLOR_REGEX = r"^\[(?:((?: ?-?\d*(?:\.\d+)? ){3}(?:-?\d*(?:\.\d+)?)) ?, ?)+((?:-?\d*(?:\.\d+)? ){3}(?:\d*(:?\.\d+)? ?))\]$"
    ALPHA_REGEX = r"^\[(?:((?: ?-?\d*(?:\.\d+)? ){1}(?:-?\d*(?:\.\d+)?)) ?, ?)+((?:-?\d*(?:\.\d+)? ){1}(?:\d*(:?\.\d+)? ?))\]$"

    color = models.TextField(validators=[RegexValidator(regex=COLOR_REGEX)])
    alpha = models.TextField(validators=[RegexValidator(regex=ALPHA_REGEX)])
    color_invert = models.TextField(
        blank=True, validators=[RegexValidator(regex=COLOR_REGEX)]
    )
    alpha_invert = models.TextField(
        blank=True, validators=[RegexValidator(regex=ALPHA_REGEX)]
    )

    range_min = models.SmallIntegerField(default=0)
    range_max = models.SmallIntegerField(default=4095)
    relative = models.BooleanField(default=False)

    color_interpolation = models.CharField(
        max_length=8,
        choices=COLOR_INTERPOLATION_CHOICES,
        default=COLOR_INTERPOLATION_RGB,
    )
    color_interpolation_invert = models.CharField(
        max_length=8,
        choices=COLOR_INTERPOLATION_CHOICES,
        default=COLOR_INTERPOLATION_RGB,
    )

    class Meta(TitleSlugDescriptionModel.Meta):
        ordering = ("title",)

    def __str__(self):
        return f"{self.title}"

    def clean(self):
        super().clean()
        color_points = len(self.color.split(","))
        alpha_points = len(self.alpha.split(","))
        if color_points != alpha_points:
            raise ValidationError(
                "The color and alpha LUT should have the same number of elements"
            )

        if self.color_invert or self.alpha_invert:
            color_invert_points = len(self.color_invert.split(","))
            alpha_invert_points = len(self.alpha_invert.split(","))
            if color_invert_points != alpha_invert_points:
                raise ValidationError(
                    "The color invert and alpha invert LUT should have the same number of elements"
                )
