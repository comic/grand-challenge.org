from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Div, Layout, Submit
from django import forms
from django.core.exceptions import ValidationError
from jsonschema import ValidationError as JSONValidationError
from jsonschema import validate

from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.hanging_protocols.models import (
    HANGING_PROTOCOL_SCHEMA,
    VIEW_CONTENT_SCHEMA,
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

    @staticmethod
    def _validate_viewport_uniqueness(viewports):
        errors = []
        if len(set(viewports)) != len(viewports):
            errors.append("Each viewport can only be used once.")
        return errors

    @staticmethod
    def _validate_dimensions(value):
        errors = []
        dims = ["x", "y", "w", "h"]
        if any(d in [k for v in value for k in v.keys()] for d in dims):
            for viewport in value:
                if not all(d in viewport for d in dims):
                    missing_dims = [d for d in dims if d not in viewport]
                    errors.append(
                        f"Either none or all viewports must have x, y, w, and h keys. Viewport {viewport['viewport_name']} missing {', '.join(missing_dims)}."
                    )
        else:
            for viewport in value:
                if any(d in viewport for d in dims):
                    missing_dims = [d for d in dims if d not in viewport]
                    errors.append(
                        f"Either none or all viewports must have x, y, w, and h keys. Viewport {viewport['viewport_name']} missing {', '.join(missing_dims)}."
                    )
        return errors

    @staticmethod
    def _validate_parent_id(viewport, viewports):
        errors = []
        if viewport.get("draggable", False) is False:
            errors.append(
                f"Viewport {viewport['viewport_name']} has a parent_id but is not draggable."
            )
        if viewport["parent_id"] not in viewports:
            errors.append(
                f"Viewport {viewport['viewport_name']} has a parent_id that does not exist."
            )
        return errors

    @staticmethod
    def _validate_slice_plane_indicator(viewport, viewports):
        errors = []
        if viewport["slice_plane_indicator"] not in viewports:
            errors.append(
                f"Viewport {viewport['viewport_name']} has a slice_plane_indicator that does not exist."
            )
        if viewport["slice_plane_indicator"] == viewport["viewport_name"]:
            errors.append(
                f"Viewport {viewport['viewport_name']} has a slice_plane_indicator that is the same as the viewport_name."
            )
        return errors

    def clean_json(self):
        def add_errors(errors):
            for error in errors:
                self.add_error(error=error, field="json")

        json = self.cleaned_data["json"]
        viewport_names = [x["viewport_name"] for x in json]
        add_errors(self._validate_viewport_uniqueness(viewport_names))
        add_errors(self._validate_dimensions(json))
        for viewport in json:
            if "parent_id" in viewport:
                add_errors(self._validate_parent_id(viewport, viewport_names))
            if "slice_plane_indicator" in viewport:
                add_errors(
                    self._validate_slice_plane_indicator(
                        viewport, viewport_names
                    )
                )
        return json


class ViewContentMixin:
    def clean_view_content(self):
        mapping = self.cleaned_data["view_content"] or {}
        try:
            validate(mapping, VIEW_CONTENT_SCHEMA)
        except JSONValidationError as e:
            raise ValidationError(f"JSON does not fulfill schema: {e}")
        hanging_protocol = self.cleaned_data["hanging_protocol"]
        if mapping and hanging_protocol:
            if set(mapping.keys()) != {
                x["viewport_name"] for x in hanging_protocol.json
            }:
                raise ValidationError(
                    "Image ports in view_content do not match "
                    "those in the selected hanging protocol."
                )

        slugs = {slug for viewport in mapping.values() for slug in viewport}
        unknown = []
        for slug in slugs:
            if not ComponentInterface.objects.filter(slug=slug).exists():
                unknown.append(slug)
        if len(unknown) > 0:
            raise ValidationError(
                f"Unkown slugs in view_content: {', '.join(unknown)}"
            )

        return mapping

    class Meta:
        widgets = {
            "view_content": JSONEditorWidget(schema=VIEW_CONTENT_SCHEMA),
        }
        help_texts = {
            "view_content": (
                "Indicate which Component Interfaces need to be displayed in "
                'which image port. E.g. {"main": ["interface1"]}. The first '
                "item in the list of interfaces will be the main image in "
                "the image port. The first overlay type interface thereafter "
                "will be rendered as an overlay. For now, any other items "
                "will be ignored by the viewer."
            )
        }
