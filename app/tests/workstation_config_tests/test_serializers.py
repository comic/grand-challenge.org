import pytest

from grandchallenge.workstation_configs.serializers import (
    WorkstationConfigSerializer,
)
from tests.factories import WorkstationConfigFactory
from tests.serializer_helpers import check_if_field_in_serializer


@pytest.mark.django_db
def test_serializer_fields():
    serializer = WorkstationConfigSerializer(WorkstationConfigFactory())

    check_if_field_in_serializer(
        serializer_fields=serializer.data.keys(),
        fields=(
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
            "default_image_interpolation",
            "overlay_segments",
            "key_bindings",
            "default_zoom_scale",
            "show_image_info_plugin",
            "show_display_plugin",
            "show_image_switcher_plugin",
            "show_algorithm_output_plugin",
            "show_overlay_plugin",
            "show_annotation_statistics_plugin",
            "show_invert_tool",
            "show_flip_tool",
            "show_window_level_tool",
            "show_reset_tool",
            "show_overlay_selection_tool",
            "show_lut_selection_tool",
            "show_annotation_counter_tool",
            "enabled_preprocessors",
            "auto_jump_center_of_gravity",
            "link_images",
            "link_panning",
            "link_zooming",
            "link_slicing",
            "link_orienting",
            "link_windowing",
            "link_inverting",
            "link_flipping",
        ),
    )
