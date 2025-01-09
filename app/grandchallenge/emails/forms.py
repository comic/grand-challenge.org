from django import forms

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorFullPageWidget
from grandchallenge.emails.models import Email


class EmailMetadataForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = Email
        fields = ("subject",)


class EmailBodyForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = Email
        fields = ("body",)
        widgets = {
            "body": MarkdownEditorFullPageWidget,
        }
