from django.forms import ModelForm, TextInput

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.organizations.models import Organization


class OrganizationForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = Organization
        fields = (
            "title",
            "description",
            "logo",
            "location",
            "website",
            "detail_page_markdown",
        )
        widgets = {
            "detail_page_markdown": MarkdownEditorWidget,
            "description": TextInput,
        }
