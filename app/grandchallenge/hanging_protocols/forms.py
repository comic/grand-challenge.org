from django import forms

from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.hanging_protocols.models import (
    IMAGE_PORT_MAPPING_SCHEMA,
    HangingProtocol,
)


class HangingProtocolForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = HangingProtocol
        fields = ("title", "description", "json")
        widgets = {"json": JSONEditorWidget}


class ImagePortMappingMixin:
    def clean_image_port_mapping(self):
        mapping = self.cleaned_data["image_port_mapping"]
        hanging_protocol = self.cleaned_data["hanging_protocol"]
        if mapping and not hanging_protocol:
            self.add_error(
                error="Please select a hanging protocol before filling this field.",
                field="image_port_mapping",
            )

        if mapping and hanging_protocol:
            if set(mapping.keys()) != {
                x["viewport_name"] for x in hanging_protocol.json
            }:
                self.add_error(
                    error=(
                        "Image ports in image_port_mapping do not match "
                        "those in the selected hanging protocol."
                    ),
                    field="image_port_mapping",
                )

        slugs = {slug for viewport in mapping.values() for slug in viewport}
        unknown = []
        for slug in slugs:
            if not ComponentInterface.objects.filter(slug=slug).exists():
                unknown.append(slug)
        if len(unknown) > 0:
            self.add_error(
                error=f"Unkown slugs in image_port_mapping: {', '.join(unknown)}",
                field="image_port_mapping",
            )

        return mapping

    class Meta:
        widgets = {
            "image_port_mapping": JSONEditorWidget(
                schema=IMAGE_PORT_MAPPING_SCHEMA
            ),
        }
        help_texts = {
            "image_port_mapping": (
                "Indicate which Component Interfaces need to be displayed in "
                'which image port. E.g. {"main": ["interface1"]}. The first '
                "item in the list of interfaces will be the main image in "
                "the image port. All subsequent items will be rendered as "
                "overlays."
            )
        }
