from collections import OrderedDict
from typing import Optional, Dict

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Submit
from django.forms import ModelForm

from grandchallenge.core.widgets import ColorEditorWidget, JSONEditorWidget
from grandchallenge.workstation_configs.models import (
    KEY_BINDINGS_SCHEMA,
    OVERLAY_SEGMENTS_SCHEMA,
    WorkstationConfig,
    VisualGroups,
)


class WorkstationConfigForm(ModelForm):
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
            "default_image_interpolation",
            "default_limit_view_area_to_image_volume",
            "default_overlay_interpolation",
            "ghosting_slice_depth",
            "overlay_segments",
            "key_bindings",
            "default_zoom_scale",
            "default_brush_size",
            "default_annotation_color",
            "default_annotation_line_width",
            "auto_jump_center_of_gravity",
            "show_image_info_plugin",
            "show_display_plugin",
            "show_image_switcher_plugin",
            "show_algorithm_output_plugin",
            "show_overlay_plugin",
            "show_annotation_statistics_plugin",
            "show_swivel_tool",
            "show_invert_tool",
            "show_flip_tool",
            "show_window_level_tool",
            "show_reset_tool",
            "show_overlay_selection_tool",
            "show_lut_selection_tool",
            "show_annotation_counter_tool",
            "enable_contrast_enhancement",
            "link_images",
            "link_panning",
            "link_zooming",
            "link_slicing",
            "link_orienting",
            "link_windowing",
            "link_inverting",
            "link_flipping",
        )

        widgets = {
            "overlay_segments": JSONEditorWidget(
                schema=OVERLAY_SEGMENTS_SCHEMA
            ),
            "key_bindings": JSONEditorWidget(schema=KEY_BINDINGS_SCHEMA),
            "default_annotation_color": ColorEditorWidget(format="hex"),
        }
        help_texts = {
            "overlay_segments": (
                model._meta.get_field("overlay_segments").help_text
                + ". If an categorical overlay is shown, it is possible to show toggles "
                "to change the visibility of the different overlay categories. To do "
                "so, configure the categories that should be displayed. Data from the"
                " algorithm's output.json can be added as an extra label to each "
                "toggle using jinja templating. "
                'For example: [{ "voxel_value": 0, "name": "Level 0", "visible": '
                'false, "metric_template": "{{metrics.volumes[0]}} mm³"},]'
            ),
            "window_presets": model._meta.get_field("window_presets").help_text
            + ". Select multiple presets by holding CTRL or dragging your mouse",
            "overlay_luts": model._meta.get_field("overlay_luts").help_text
            + ". Select multiple presets by holding CTRL or dragging your mouse",
            "key_bindings": model._meta.get_field("key_bindings").help_text
            + ". A copy and paste JSON can be obtained from the viewer",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ordered_fields = list(self.fields.keys())
        DEFAULT_NAME = None
        field_set_groups: Dict[Optional[str], list] = OrderedDict(
            (
                (DEFAULT_NAME, []),
                *[(k, []) for k in VisualGroups.group_map.keys()],
            )
        )
        for field_name in ordered_fields:
            for group_name, field_list in reversed(field_set_groups.items()):
                if (
                    DEFAULT_NAME == group_name
                    or field_name in VisualGroups.group_map[group_name].names
                ):
                    field_list.append(field_name)
                    break

        helper_fields = []
        for group_name, field_list in field_set_groups.items():
            if group := VisualGroups.group_map.get(group_name):
                helper_fields.append(HTML(f"<h2>{group.title}</h2>"))
                if desc := group.description:
                    helper_fields.append(
                        HTML(f'<p class="text-muted">{desc}</p>')
                    )
            helper_fields.extend(field_list)

        self.helper = FormHelper()
        self.helper.layout = Layout(*helper_fields)
        self.helper.layout.append(Submit("save", "Save"))
