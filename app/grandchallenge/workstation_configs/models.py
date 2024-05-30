from collections import OrderedDict
from functools import cached_property
from typing import Sequence, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import PositiveSmallIntegerField
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm
from panimg.models import MAXIMUM_SEGMENTS_LENGTH

from grandchallenge.core.fields import HexColorField
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
        "maxItems": MAXIMUM_SEGMENTS_LENGTH,
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


class Group:
    title: str
    description: Optional[str]
    items: List[models.Field]

    @cached_property
    def names(self):
        return tuple(i.name for i in self.items)

    def __init__(self, *, title, description=None):
        self.title = title
        self.description = description
        self.items = []

    def __set_name__(self, owner, name):
        owner.group_map[name] = self

    def add_to_group(self, other):
        self.items.append(other)
        if "names" in vars(self):
            del vars(self)["names"]


class VisualGroups:
    __instance = None

    group_map: Dict[str, Group] = OrderedDict()
    _default = Group(title="")
    annotations = Group(
        title="Annotations and Overlays",
        description="Behavior or visualization settings for annotations and overlays.",
    )
    plugins_tools = Group(
        title="Plugin and Tools",
        description="Plugins are components of the viewer, whereas tools are "
        "(generally) contained within plugins.",
    )
    linking = Group(
        title="Linking Configuration",
        description="Linked images share tool interactions and display properties, "
        "it is possible to manually (un)link them during viewing.",
    )

    def __new__(cls) -> "VisualGroups":
        if not (result := cls.__instance):
            cls.__instance = result = super().__new__(cls)
        return result


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
        MPMRI = "MPMRI", "Multiparametric MRI"

    class ImageInterpolationType(models.TextChoices):
        NEAREST = "NN", "NearestNeighbor"  # Maps to FILTER_NEAREST in MeVisLab
        TRILINEAR = "TL", "Trilinear"  # Maps to FILTER_LINEAR in MeVisLab
        CUBIC = "CU", "Cubic"  # Maps to FILTER_CUBIC_POSTCLASS in MeVisLab

    creator = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.SET_NULL
    )

    window_presets = models.ManyToManyField(
        to="WindowPreset",
        blank=True,
        related_name="workstation_window_presets",
        help_text="Window-preset options that change the projection of (computed) "
        "image values to displayed pixels",
    )

    default_window_preset = models.ForeignKey(
        to="WindowPreset",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="workstation_default_window_presets",
        help_text="The preset that is applied when an image is first shown",
    )

    image_context = models.CharField(
        blank=True,
        max_length=6,
        choices=ImageContext.choices,
        help_text="Sets several heuristics used for automatically selecting tools, hanging protocols, et cetera",
    )

    # 4 digits, 2 decimal places, 0.01 min, 99.99 max
    default_slab_thickness_mm = models.DecimalField(
        blank=True,
        null=True,
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(limit_value=0.01)],
        help_text="The size (depth/Z size) in millimeters used to project image values "
        "to displayed pixels",
    )

    default_slab_render_method = models.CharField(
        max_length=3,
        choices=SlabRenderMethod.choices,
        blank=True,
        help_text="The method used to project multiple voxels in the volume, found within "
        "the slab thickness column, to displayed pixels",
    )

    default_orientation = models.CharField(
        max_length=1,
        choices=Orientation.choices,
        blank=True,
        help_text="The orientation that defines the 3D-intersection plane used to render slabs of 3D images",
    )

    ghosting_slice_depth = models.PositiveSmallIntegerField(
        default=3,
        blank=False,
        help_text="The number of slices a polygon annotation should remain visible for on slices surrounding the annotation slice.",
    )
    VisualGroups().annotations.add_to_group(ghosting_slice_depth)

    overlay_luts = models.ManyToManyField(
        to="LookUpTable",
        blank=True,
        related_name="workstation_overlay_luts",
        help_text="The preset look-up tables options that are used to project overlay-image values to "
        "displayed pixel colors",
    )
    VisualGroups().annotations.add_to_group(overlay_luts)

    default_overlay_lut = models.ForeignKey(
        to="LookUpTable",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The look-up table that is applied when an overlay image is first shown",
    )
    VisualGroups().annotations.add_to_group(default_overlay_lut)

    default_overlay_interpolation = models.CharField(
        max_length=2,
        choices=ImageInterpolationType.choices,
        default=ImageInterpolationType.NEAREST,
        blank=True,
        help_text="The method used to interpolate multiple voxels of overlay images and project them to screen pixels",
    )
    VisualGroups().annotations.add_to_group(default_overlay_interpolation)

    default_image_interpolation = models.CharField(
        max_length=2,
        choices=ImageInterpolationType.choices,
        default=ImageInterpolationType.CUBIC,
        blank=True,
        help_text="The method used to interpolate multiple voxels of the image and project them to screen pixels",
    )

    default_limit_view_area_to_image_volume = models.BooleanField(
        default=False,
        help_text="When enabled, the view area is limited to the image volume, ensuring that changes in orientation and panning do not obscure parts of the image",
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
        help_text="The alpha value used for setting the degree of opacity for displayed pixels of overlay images",
    )
    VisualGroups().annotations.add_to_group(default_overlay_alpha)

    overlay_segments = models.JSONField(
        default=list,
        blank=True,
        validators=[JSONValidator(schema=OVERLAY_SEGMENTS_SCHEMA)],
        help_text="The schema that defines how categories of values in the overlay images are differentiated",
    )
    VisualGroups().annotations.add_to_group(overlay_segments)

    key_bindings = models.JSONField(
        default=list,
        blank=True,
        validators=[JSONValidator(schema=KEY_BINDINGS_SCHEMA)],
        help_text="The schema that overwrites the mapping between keyboard shortcuts and viewer actions",
    )

    # 4 digits, 2 decimal places, 0.01 min, 99.99 max
    default_zoom_scale = models.DecimalField(
        blank=True,
        null=True,
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(limit_value=0.01)],
    )

    default_brush_size = models.DecimalField(
        blank=True,
        null=True,
        max_digits=16,  # 1000 km
        decimal_places=7,
        validators=[MinValueValidator(limit_value=1e-6)],  # 1 nm
        help_text="Default brush diameter in millimeters for creating annotations",
    )
    VisualGroups().annotations.add_to_group(default_brush_size)

    default_annotation_color = HexColorField(
        blank=True,
        null=True,
        help_text="Default color for displaying and creating annotations",
    )
    VisualGroups().annotations.add_to_group(default_annotation_color)

    default_annotation_line_width = PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="Default line width in pixels for displaying and creating annotations",
    )
    VisualGroups().annotations.add_to_group(default_annotation_line_width)

    show_image_info_plugin = models.BooleanField(
        default=True,
        help_text="A plugin that shows meta-data information derived from image headers "
        "as well as any configured case text for reader studies",
    )
    VisualGroups().plugins_tools.add_to_group(show_image_info_plugin)

    show_display_plugin = models.BooleanField(
        default=True,
        help_text="A plugin that allows control over display properties such as window preset, "
        "slab thickness, or orientation",
    )
    VisualGroups().plugins_tools.add_to_group(show_display_plugin)

    show_image_switcher_plugin = models.BooleanField(
        default=True,
        help_text="A plugin that allows switching images when viewing algorithm outputs",
    )
    VisualGroups().plugins_tools.add_to_group(show_image_switcher_plugin)

    show_algorithm_output_plugin = models.BooleanField(
        default=True,
        help_text="A plugin that shows algorithm outputs, including navigation controls",
    )
    VisualGroups().plugins_tools.add_to_group(show_image_switcher_plugin)

    show_overlay_plugin = models.BooleanField(
        default=True,
        help_text="A plugin that contains overlay-related controls, "
        "such as the overlay-selection tool and overlay-segmentation visibility",
    )
    VisualGroups().plugins_tools.add_to_group(show_overlay_plugin)

    show_annotation_statistics_plugin = models.BooleanField(
        default=False,
        help_text="A plugin that allows analysis of segmentations. It shows voxel value "
        "statistics of annotated areas.",
    )
    VisualGroups().plugins_tools.add_to_group(
        show_annotation_statistics_plugin
    )

    show_swivel_tool = models.BooleanField(
        default=False,
        help_text="A tool that allows swiveling the image around axes to view a custom orientation",
    )
    VisualGroups().plugins_tools.add_to_group(show_swivel_tool)

    show_invert_tool = models.BooleanField(
        default=True,
        help_text="A tool/button that allows inverting the displayed pixel colors of an image",
    )
    VisualGroups().plugins_tools.add_to_group(show_invert_tool)

    show_flip_tool = models.BooleanField(
        default=True,
        help_text="A tool/button that allows vertical flipping/mirroring of an image",
    )
    VisualGroups().plugins_tools.add_to_group(show_flip_tool)

    show_window_level_tool = models.BooleanField(
        default=True,
        help_text="A tool that allows selection of window presets and changing the window width/center",
    )
    VisualGroups().plugins_tools.add_to_group(show_window_level_tool)

    show_reset_tool = models.BooleanField(
        default=True,
        help_text="A tool/button that resets all display properties of the images to defaults",
    )
    VisualGroups().plugins_tools.add_to_group(show_reset_tool)

    show_overlay_selection_tool = models.BooleanField(
        default=True,
        help_text="A tool that allows switching overlay images when viewing algorithm outputs",
    )
    VisualGroups().plugins_tools.add_to_group(show_overlay_selection_tool)

    show_lut_selection_tool = models.BooleanField(
        default=True,
        verbose_name="Show overlay-lut selection tool",
        help_text="A tool that allows switching between the overlay-lut presets",
    )
    VisualGroups().plugins_tools.add_to_group(show_lut_selection_tool)

    show_annotation_counter_tool = models.BooleanField(
        default=True,
        help_text="A tool that can be used to show summary statistics of annotations within an area",
    )
    VisualGroups().plugins_tools.add_to_group(show_lut_selection_tool)

    link_images = models.BooleanField(
        default=True,
        help_text="Start with the images linked",
    )
    VisualGroups().linking.add_to_group(link_images)

    link_panning = models.BooleanField(
        default=True,
        help_text="When panning and the images are linked, they share any new position",
    )
    VisualGroups().linking.add_to_group(link_panning)

    link_zooming = models.BooleanField(
        default=True,
        help_text="When zooming and the images are linked, they share any new zoom level",
    )
    VisualGroups().linking.add_to_group(link_zooming)

    link_slicing = models.BooleanField(
        default=True,
        help_text="When scrolling and the images are linked, they share any slice changes",
    )
    VisualGroups().linking.add_to_group(link_slicing)

    link_orienting = models.BooleanField(
        default=True,
        help_text="When orienting and the images are linked, they share any new orientation",
    )
    VisualGroups().linking.add_to_group(link_orienting)

    link_windowing = models.BooleanField(
        default=True,
        help_text="When changing window setting and the images are linked, they share any new window width/center",
    )
    VisualGroups().linking.add_to_group(link_windowing)

    link_inverting = models.BooleanField(
        default=True,
        help_text="When inverting images and the images are linked, they share any new invert state",
    )
    VisualGroups().linking.add_to_group(link_inverting)

    link_flipping = models.BooleanField(
        default=True,
        help_text="When flipping images and the images are linked, they share any new flip state",
    )
    VisualGroups().linking.add_to_group(link_flipping)

    enable_contrast_enhancement = models.BooleanField(
        default=False,
        verbose_name="Contrast-enhancement preprocessing tool",
        help_text="A tool that uses image preprocessing to enhance contrast. "
        "It is mainly used for viewing eye-fundus images",
    )
    VisualGroups().plugins_tools.add_to_group(enable_contrast_enhancement)

    auto_jump_center_of_gravity = models.BooleanField(
        default=True,
        help_text="Enables a jump to center of gravity of the first output when viewing algorithm "
        "outputs or the first overlay segment when viewing a reader study",
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


class WorkstationConfigUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(
        WorkstationConfig, on_delete=models.CASCADE
    )


class WorkstationConfigGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(
        WorkstationConfig, on_delete=models.CASCADE
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
