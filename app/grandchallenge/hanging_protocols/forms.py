from django import forms

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


class ViewContentMixin:
    def clean_view_content(self):
        mapping = self.cleaned_data["view_content"] or {}
        hanging_protocol = self.cleaned_data["hanging_protocol"]
        if mapping and hanging_protocol:
            if set(mapping.keys()) != {
                x["viewport_name"] for x in hanging_protocol.json
            }:
                self.add_error(
                    error=(
                        "Image ports in view_content do not match "
                        "those in the selected hanging protocol."
                    ),
                    field="view_content",
                )

        slugs = {slug for viewport in mapping.values() for slug in viewport}
        unknown = []
        for slug in slugs:
            if not ComponentInterface.objects.filter(slug=slug).exists():
                unknown.append(slug)
        if len(unknown) > 0:
            self.add_error(
                error=f"Unkown slugs in view_content: {', '.join(unknown)}",
                field="view_content",
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
