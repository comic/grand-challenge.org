from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Submit
from django.forms import ModelForm

from grandchallenge.core.widgets import ColorEditorWidget, JSONEditorWidget
from grandchallenge.workstation_configs.models import (
    KEY_BINDINGS_SCHEMA,
    OVERLAY_SEGMENTS_SCHEMA,
    WorkstationConfig,
)

from .visual_field_ordering import FORM_FIELDS, GROUPS


class WorkstationConfigForm(ModelForm):
    class Meta:
        model = WorkstationConfig
        fields = FORM_FIELDS

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

        helper_fields = []
        for group in GROUPS:
            filtered_fields = [fn for fn in group.names if fn in self.fields]
            if not filtered_fields:
                continue
            helper_fields.append(HTML(f"<h2>{group.title}</h2>"))
            if desc := group.description:
                helper_fields.append(HTML(f'<p class="text-muted">{desc}</p>'))
            helper_fields.extend(filtered_fields)

        self.helper = FormHelper()
        self.helper.layout = Layout(*helper_fields)
        self.helper.layout.append(Submit("save", "Save"))
