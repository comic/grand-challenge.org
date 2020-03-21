from django.forms import ModelForm, TextInput

from grandchallenge.archives.models import Archive
from grandchallenge.core.forms import (
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.widgets import MarkdownEditorWidget


class ArchiveForm(WorkstationUserFilterMixin, SaveFormInitMixin, ModelForm):
    class Meta:
        model = Archive
        fields = (
            "title",
            "description",
            "logo",
            "workstation",
            "workstation_config",
            "detail_page_markdown",
        )
        widgets = {
            "description": TextInput,
            "detail_page_markdown": MarkdownEditorWidget,
        }
