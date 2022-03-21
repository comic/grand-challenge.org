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
