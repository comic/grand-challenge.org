from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.core.models import UUIDModel


class WorkstationConfig(TitleSlugDescriptionModel, UUIDModel):
    ORIENTATION_AXIAL = "A"
    ORIENTATION_CORONAL = "C"
    ORIENTATION_SAGITTAL = "S"

    ORIENTATION_CHOICES = (
        (ORIENTATION_AXIAL, "Axial"),
        (ORIENTATION_CORONAL, "Coronal"),
        (ORIENTATION_SAGITTAL, "Sagittal"),
    )

    SLAB_RENDER_METHOD_MAXIMUM = "MAX"
    SLAB_RENDER_METHOD_MINIMUM = "MIN"
    SLAB_RENDER_METHOD_AVERAGE = "AVG"

    SLAB_RENDER_METHOD_CHOICES = (
        (SLAB_RENDER_METHOD_MAXIMUM, "Maximum"),
        (SLAB_RENDER_METHOD_MINIMUM, "Minimum"),
        (SLAB_RENDER_METHOD_AVERAGE, "Average"),
    )

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

    # 4 digits, 2 decimal places, 0.0 min, 99.99 max
    default_slab_thickness_mm = models.DecimalField(
        blank=True,
        null=True,
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(limit_value=0.01)],
    )
    default_slab_render_method = models.CharField(
        max_length=3, choices=SLAB_RENDER_METHOD_CHOICES, blank=True
    )

    default_orientation = models.CharField(
        max_length=1, choices=ORIENTATION_CHOICES, blank=True
    )

    default_overlay_lut = models.ForeignKey(
        to="LookUpTable", blank=True, null=True, on_delete=models.SET_NULL
    )

    class Meta(TitleSlugDescriptionModel.Meta, UUIDModel.Meta):
        ordering = ("created", "creator")

    def __str__(self):
        return f"{self.title} (created by {self.creator})"


class WindowPreset(TitleSlugDescriptionModel):
    width = models.PositiveIntegerField(
        validators=[MinValueValidator(limit_value=1)]
    )
    center = models.IntegerField()

    class Meta(TitleSlugDescriptionModel.Meta):
        ordering = ("title",)

    def __str__(self):
        return f"{self.title} (center {self.center}, width {self.width})"


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

    INTERPOLATION_TYPE_NEAREST = "NearestNeighbour"
    INTERPOLATION_TYPE_TRILINEAR = "Trilinear"
    INTERPOLATION_TYPE_CHOICES = (
        (INTERPOLATION_TYPE_NEAREST, "Nearest Neighbour"),
        (INTERPOLATION_TYPE_NEAREST, "Trilinear"),
    )

    lut_color = models.TextField()
    lut_alpha = models.TextField()
    lut_color_invert = models.TextField(blank=True)
    lut_alpha_invert = models.TextField(blank=True)
    lut_range_min = models.SmallIntegerField(default=0)
    lut_range_max = models.SmallIntegerField(default=4095)
    lut_relative = models.BooleanField(default=False)

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

    interpolation = models.CharField(
        max_length=16,
        choices=INTERPOLATION_TYPE_CHOICES,
        default=INTERPOLATION_TYPE_NEAREST,
    )

    class Meta(TitleSlugDescriptionModel.Meta):
        ordering = ("title",)

    def __str__(self):
        return f"{self.title}"
