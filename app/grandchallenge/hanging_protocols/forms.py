from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.hanging_protocols.models import HangingProtocol


class HangingProtocolForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = HangingProtocol
        fields = ("title", "description", "json")
        widgets = {"json": JSONEditorWidget}
