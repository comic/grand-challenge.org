from django.forms import ModelForm

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.workstation_configs.models import (
    KEY_BINDINGS_SCHEMA,
    OVERLAY_SEGMENTS_SCHEMA,
    WorkstationConfig,
)


class WorkstationConfigForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = WorkstationConfig
        fields = (
            "title",
            "description",
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
            "enable_contrast_enhancement",
            "auto_jump_center_of_gravity",
        )
        widgets = {
            "overlay_segments": JSONEditorWidget(
                schema=OVERLAY_SEGMENTS_SCHEMA
            ),
            "key_bindings": JSONEditorWidget(schema=KEY_BINDINGS_SCHEMA),
        }
        help_texts = {
            "overlay_segments": (
                "If an categorical overlay is shown, it is possible to show toggles "
                "to change the visibility of the different overlay categories. To do "
                "so, configure the categories that should be displayed. Data from the"
                " algorithm's output.json can be added as an extra label to each "
                "toggle using jinja templating. "
                'For example: [{ "voxel_value": 0, "name": "Level 0", "visible": '
                'false, "metric_template": "{{metrics.volumes[0]}} mm³"},]'
            ),
            "image_context": "This tells the viewer how to show the images "
            "defined in the hanging list",
            "window_presets": "These are the window LUT presets the viewer can choose between. "
            "By default, none are selected. "
            "Select multiple presets by holding CTRL or dragging your mouse",
        }
