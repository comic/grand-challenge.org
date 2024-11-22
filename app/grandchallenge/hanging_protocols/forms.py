import json

from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Div, Layout, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy

from grandchallenge.components.models import (
    InterfaceKind,
    InterfaceKindChoices,
)
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.validators import JSONValidator
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.hanging_protocols.models import (
    HANGING_PROTOCOL_SCHEMA,
    VIEW_CONTENT_SCHEMA,
    HangingProtocol,
    ViewportNames,
)
from grandchallenge.subdomains.utils import reverse


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


class ViewContentExampleMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            interface_slugs = self.instance.interfaces.values_list(
                "slug", flat=True
            )

            if interface_slugs.count() > 0:
                self.fields[
                    "view_content"
                ].help_text += f"The following interfaces are used in your {self.instance._meta.verbose_name}: {oxford_comma(interface_slugs)}. "

            view_content_example = self.generate_view_content_example()

            if view_content_example:
                self.fields[
                    "view_content"
                ].help_text += f"Example usage: {view_content_example}. "
            else:
                self.fields[
                    "view_content"
                ].help_text += "No interfaces of type image, chart, pdf, mp4, thumbnail_jpg or thumbnail_png are used. At least one interface of those types is needed to configure the viewer. "

        self.fields["view_content"].help_text += format_lazy(
            'Refer to the <a href="{}">documentation</a> for more information',
            reverse("documentation:detail", args=["viewer-content"]),
        )

    def generate_view_content_example(self):
        images = list(
            self.instance.interfaces.filter(
                kind=InterfaceKindChoices.IMAGE
            ).values_list("slug", flat=True)
        )
        mandatory_isolation_interfaces = list(
            self.instance.interfaces.filter(
                kind__in=InterfaceKind.interface_type_mandatory_isolation()
            ).values_list("slug", flat=True)
        )

        if not images and not mandatory_isolation_interfaces:
            return None

        overlays = list(
            self.instance.interfaces.exclude(
                kind__in=InterfaceKind.interface_type_undisplayable()
                | InterfaceKind.interface_type_mandatory_isolation()
                | {InterfaceKindChoices.IMAGE}
            ).values_list("slug", flat=True)
        )
        if images:
            overlays_per_image = len(overlays) // len(images)
            remaining_overlays = len(overlays) % len(images)

        view_content_example = {}

        for port in ViewportNames.values:
            if mandatory_isolation_interfaces:
                view_content_example[port] = [
                    mandatory_isolation_interfaces.pop(0)
                ]
            elif images:
                view_content_example[port] = [images.pop(0)]
                for _ in range(overlays_per_image):
                    view_content_example[port].append(overlays.pop(0))
                if remaining_overlays > 0:
                    view_content_example[port].append(overlays.pop(0))
                    remaining_overlays -= 1

        try:
            JSONValidator(schema=VIEW_CONTENT_SCHEMA)(
                value=view_content_example
            )
            self.instance.clean_view_content(
                view_content_example, self.instance.hanging_protocol
            )
        except ValidationError as error:
            raise RuntimeError("view_content example is not valid.") from error

        return json.dumps(view_content_example)
