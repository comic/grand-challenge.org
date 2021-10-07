from rest_framework.fields import CharField, FloatField
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from grandchallenge.workstation_configs.models import (
    LookUpTable,
    WindowPreset,
    WorkstationConfig,
)


class WindowPresetSerializer(ModelSerializer):
    class Meta:
        model = WindowPreset
        fields = [
            "pk",
            "slug",
            "title",
            "description",
            "center",
            "width",
            "lower_percentile",
            "upper_percentile",
        ]


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
    image_context = CharField(
        source="get_image_context_display", read_only=True
    )
    default_slab_render_method = CharField(
        source="get_default_slab_render_method_display", read_only=True
    )
    default_orientation = CharField(
        source="get_default_orientation_display", read_only=True
    )
    default_slab_thickness_mm = FloatField()
    window_presets = WindowPresetSerializer(many=True, read_only=True)
    default_window_preset = WindowPresetSerializer()
    overlay_luts = LookUpTableSerializer(many=True, read_only=True)
    default_overlay_lut = LookUpTableSerializer()
    default_overlay_interpolation = CharField(
        source="get_default_overlay_interpolation_display", read_only=True
    )
    default_overlay_alpha = FloatField()
    default_zoom_scale = FloatField()

    enabled_preprocessors = SerializerMethodField()

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
            "image_context",
            "window_presets",
            "default_window_preset",
            "default_slab_thickness_mm",
            "default_slab_render_method",
            "default_orientation",
            "default_overlay_alpha",
            "overlay_luts",
            "default_overlay_lut",
            "default_overlay_interpolation",
            "overlay_segments",
            "key_bindings",
            "default_zoom_scale",
            "show_image_info_plugin",
            "show_display_plugin",
            "show_image_switcher_plugin",
            "show_algorithm_output_plugin",
            "show_overlay_plugin",
            "show_invert_tool",
            "show_flip_tool",
            "show_window_level_tool",
            "show_reset_tool",
            "show_overlay_selection_tool",
            "show_lut_selection_tool",
            "show_annotation_counter_tool",
            "enabled_preprocessors",
            "auto_jump_center_of_gravity",
        ]

    def get_enabled_preprocessors(self, obj):
        if obj.enable_contrast_enhancement:
            text = ["contrast_enhanced"]
        else:
            text = []
        return text
