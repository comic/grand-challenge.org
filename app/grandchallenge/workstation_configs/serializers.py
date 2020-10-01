from rest_framework.fields import CharField, FloatField
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ModelSerializer

from grandchallenge.workstation_configs.models import (
    LookUpTable,
    WindowPreset,
    WorkstationConfig,
)


class WindowPresetSerializer(ModelSerializer):
    class Meta:
        model = WindowPreset
        fields = ["pk", "slug", "title", "description", "center", "width"]


class LookUpTableSerializer(ModelSerializer):
    class Meta:
        model = LookUpTable
        fields = [
            "pk",
            "slug",
            "title",
            "description",
            "color",
            "alpha",
            "color_invert",
            "alpha_invert",
            "range_min",
            "range_max",
            "relative",
            "color_interpolation",
            "color_interpolation_invert",
        ]


class WorkstationConfigSerializer(ModelSerializer):
    creator = SlugRelatedField(read_only=True, slug_field="username")
    default_slab_render_method = CharField(
        source="get_default_slab_render_method_display"
    )
    default_orientation = CharField(source="get_default_orientation_display")
    default_slab_thickness_mm = FloatField()
    window_presets = WindowPresetSerializer(many=True, read_only=True)
    default_window_preset = WindowPresetSerializer()
    default_overlay_lut = LookUpTableSerializer()
    default_overlay_interpolation = CharField(
        source="get_default_overlay_interpolation_display"
    )
    default_overlay_alpha = FloatField()
    default_zoom_scale = FloatField()

    class Meta:
        model = WorkstationConfig
        fields = [
            "pk",
            "slug",
            "title",
            "description",
            "created",
            "modified",
            "creator",
            "window_presets",
            "default_window_preset",
            "default_slab_thickness_mm",
            "default_slab_render_method",
            "default_orientation",
            "default_overlay_alpha",
            "default_overlay_lut",
            "default_overlay_interpolation",
            "overlay_segments",
            "key_bindings",
            "default_zoom_scale",
            "show_image_info_plugin",
            "show_display_plugin",
            "show_invert_tool",
            "show_flip_tool",
            "show_window_level_tool",
            "show_reset_tool",
        ]
