from django.forms import ModelForm

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.workstation_configs.models import (
    OVERLAY_SEGMENTS_SCHEMA,
    WorkstationConfig,
)


class WorkstationConfigForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = WorkstationConfig
        fields = (
            "title",
            "description",
            "window_presets",
            "default_window_preset",
            "default_slab_thickness_mm",
            "default_slab_render_method",
            "default_orientation",
            "default_overlay_alpha",
            "default_overlay_lut",
            "default_overlay_interpolation",
            "overlay_segments",
            "default_zoom_scale",
            "show_image_info_plugin",
            "show_display_plugin",
            "show_invert_tool",
            "show_flip_tool",
            "show_window_level_tool",
            "show_reset_tool",
        )
        widgets = {
            "overlay_segments": JSONEditorWidget(
                schema=OVERLAY_SEGMENTS_SCHEMA
            ),
        }
