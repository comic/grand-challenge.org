from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Div, Layout, Submit
from django import forms

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.hanging_protocols.models import (
    HANGING_PROTOCOL_SCHEMA,
    HangingProtocol,
)


class HangingProtocolForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = HangingProtocol
        fields = ("title", "description", "json")
        widgets = {"json": JSONEditorWidget(schema=HANGING_PROTOCOL_SCHEMA)}
        help_texts = {
            "json": (
                "To display a single image in full size, define the "
                "protocol as follows: "
                '[{"viewport_name": "main", "x": 0,"y": 0,"w": 1,"h": 1,'
                '"fullsizable": true,"draggable": false,"selectable": true,'
                '"order": 0}]'
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
                "title",
                "description",
                "json",
                Div(
                    id="hpVisualization",
                    css_class="container-fluid m-1 mb-3 position-relative",
                    style="height: 250px",
                ),
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    def clean_json(self):
        json = self.cleaned_data["json"]
        viewport_names = [x["viewport_name"] for x in json]

        self._validate_viewport_uniqueness(viewport_names=viewport_names)
        self._validate_dimensions(value=json)

        for viewport in json:
            if "parent_id" in viewport:
                self._validate_parent_id(
                    viewport=viewport, viewport_names=viewport_names
                )
            if "slice_plane_indicator" in viewport:
                self._validate_slice_plane_indicator(
                    viewport=viewport, viewport_names=viewport_names
                )

        return json

    def _validate_viewport_uniqueness(self, *, viewport_names):
        if len(set(viewport_names)) != len(viewport_names):
            self.add_error(
                error="Each viewport can only be used once.", field="json"
            )

    def _validate_dimensions(self, *, value):
        dims = ["x", "y", "w", "h"]
        if any(d in [k for v in value for k in v.keys()] for d in dims):
            for viewport in value:
                if not all(d in viewport for d in dims):
                    missing_dims = [d for d in dims if d not in viewport]
                    self.add_error(
                        error=f"Either none or all viewports must have x, y, w, and h keys. Viewport {viewport['viewport_name']} missing {', '.join(missing_dims)}.",
                        field="json",
                    )
        else:
            for viewport in value:
                if any(d in viewport for d in dims):
                    missing_dims = [d for d in dims if d not in viewport]
                    self.add_error(
                        error=f"Either none or all viewports must have x, y, w, and h keys. Viewport {viewport['viewport_name']} missing {', '.join(missing_dims)}.",
                        field="json",
                    )

    def _validate_parent_id(self, *, viewport, viewport_names):
        if viewport.get("draggable", False) is False and not viewport.get(
            "specialized_view"
        ) in ["minimap", "3D-sideview", "intensity-over-time-chart"]:
            self.add_error(
                error=f"Viewport {viewport['viewport_name']} has a parent_id but is not draggable or is not a specialized view.",
                field="json",
            )
        if viewport["parent_id"] not in viewport_names:
            self.add_error(
                error=f"Viewport {viewport['viewport_name']} has a parent_id that does not exist.",
                field="json",
            )
        if viewport["parent_id"] == viewport["viewport_name"]:
            self.add_error(
                error=f"Viewport {viewport['viewport_name']} has itself set as parent_id. Choose a different viewport as parent_id.",
                field="json",
            )

    def _validate_slice_plane_indicator(self, *, viewport, viewport_names):
        if viewport["slice_plane_indicator"] not in viewport_names:
            self.add_error(
                error=f"Viewport {viewport['viewport_name']} has a slice_plane_indicator that does not exist.",
                field="json",
            )
        if viewport["slice_plane_indicator"] == viewport["viewport_name"]:
            self.add_error(
                error=f"Viewport {viewport['viewport_name']} has a slice_plane_indicator that is the same as the viewport_name.",
                field="json",
            )
