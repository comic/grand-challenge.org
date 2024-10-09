from django import forms

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorInlineWidget
from grandchallenge.emails.models import Email


class EmailForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = Email
        fields = (
            "subject",
            "body",
        )
        widgets = {"body": MarkdownEditorInlineWidget}
