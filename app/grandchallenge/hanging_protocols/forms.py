import json
from typing import NamedTuple

from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Div, Layout, Submit
from django import forms
from django.conf import settings
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
        hanging_protocol_json = self.cleaned_data["json"]

        try:
            viewport_names = [
                viewport["viewport_name"] for viewport in hanging_protocol_json
            ]
        except (KeyError, TypeError):
            raise ValidationError(
                "Hanging protocol definition is invalid. Have a look at the example in the helptext."
            )

        self._validate_viewport_uniqueness(viewport_names=viewport_names)
        self._validate_dimensions(value=hanging_protocol_json)

        for viewport in hanging_protocol_json:
            if "parent_id" in viewport:
                self._validate_parent_id(
                    viewport=viewport, viewport_names=viewport_names
                )
            if "slice_plane_indicator" in viewport:
                self._validate_slice_plane_indicator(
                    viewport=viewport, viewport_names=viewport_names
                )

        return hanging_protocol_json

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


class InterfaceLists(NamedTuple):
    images: list[str]
    mandatory_isolation_interfaces: list[str]
    overlays: list[str]


class ViewContentExampleMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            interface_slugs = [
                interface.slug
                for interface in self.instance.linked_component_interfaces
            ]

            if len(interface_slugs) > 0:
                self.fields[
                    "view_content"
                ].help_text += f"The following sockets are used in your {self.instance._meta.verbose_name}: {oxford_comma(interface_slugs)}. "

            view_content_example = self.generate_view_content_example()

            if view_content_example:
                self.fields[
                    "view_content"
                ].help_text += f"Example usage: {view_content_example}. "
            else:
                self.fields[
                    "view_content"
                ].help_text += "No sockets of type image, chart, pdf, mp4, thumbnail_jpg or thumbnail_png are used. At least one socket of those types is needed to configure the viewer. "

        self.fields["view_content"].help_text += format_lazy(
            'Refer to the <a href="{}">documentation</a> for more information',
            reverse(
                "documentation:detail",
                kwargs={
                    "slug": settings.DOCUMENTATION_HELP_VIEWER_CONTENT_SLUG
                },
            ),
        )

    def _get_interface_lists(self):
        sorted_interfaces = sorted(
            list(self.instance.linked_component_interfaces),
            key=lambda x: x.slug,
        )
        images = [
            interface.slug
            for interface in sorted_interfaces
            if interface.kind == InterfaceKindChoices.PANIMG_IMAGE
        ]
        mandatory_isolation_interfaces = [
            interface.slug
            for interface in sorted_interfaces
            if interface.kind
            in InterfaceKind.interface_type_mandatory_isolation()
        ]
        overlays = [
            interface.slug
            for interface in sorted_interfaces
            if interface.kind
            not in (
                *InterfaceKind.interface_type_undisplayable(),
                *InterfaceKind.interface_type_mandatory_isolation(),
                InterfaceKindChoices.PANIMG_IMAGE,
            )
        ]
        return InterfaceLists(
            images=images,
            mandatory_isolation_interfaces=mandatory_isolation_interfaces,
            overlays=overlays,
        )

    def _get_viewports(self):
        if self.instance.hanging_protocol:
            return {
                x["viewport_name"]
                for x in self.instance.hanging_protocol.json
                if "viewport_name" in x
            }
        return ViewportNames.values

    def _build_view_content(
        self, images, mandatory_isolation_interfaces, overlays, viewports
    ):
        view_content_example = {}

        if self.instance.hanging_protocol:
            viewport_count = len(viewports)

            if mandatory_isolation_interfaces:
                mandatory_isolation_interfaces = (
                    mandatory_isolation_interfaces
                    * (viewport_count // len(mandatory_isolation_interfaces))
                    + mandatory_isolation_interfaces[
                        : (
                            viewport_count
                            % len(mandatory_isolation_interfaces)
                        )
                    ]
                )
                viewport_count -= len(mandatory_isolation_interfaces)

            if images:
                images = (
                    images * (viewport_count // len(images))
                    + images[: (viewport_count % len(images))]
                )

        overlays_per_image = len(overlays) // len(images) if images else 0
        remaining_overlays = len(overlays) % len(images) if images else 0

        for port in viewports:
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

        return view_content_example

    def generate_view_content_example(self):
        interface_lists = self._get_interface_lists()
        if (
            not interface_lists.images
            and not interface_lists.mandatory_isolation_interfaces
        ):
            return None

        viewports = self._get_viewports()
        view_content_example = self._build_view_content(
            interface_lists.images.copy(),
            interface_lists.mandatory_isolation_interfaces.copy(),
            interface_lists.overlays.copy(),
            viewports,
        )

        try:
            JSONValidator(schema=VIEW_CONTENT_SCHEMA)(
                value=view_content_example
            )
            self.instance.clean_view_content(
                view_content=view_content_example,
                hanging_protocol=self.instance.hanging_protocol,
            )
        except ValidationError as error:
            raise RuntimeError("view_content example is not valid.") from error

        return json.dumps(view_content_example)
