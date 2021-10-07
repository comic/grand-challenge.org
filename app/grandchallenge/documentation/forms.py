from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.db.models import BLANK_CHOICE_DASH

from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.documentation.models import DocPage


class DocPageCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = DocPage
        fields = (
            "title",
            "content",
            "parent",
        )
        widgets = {"content": MarkdownEditorWidget}


class DocPageUpdateForm(DocPageCreateForm):
    """Like the create form but you can also move the page."""

    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices = (
        (BLANK_CHOICE_DASH[0]),
        (DocPage.FIRST, "First"),
        (DocPage.UP, "Up"),
        (DocPage.DOWN, "Down"),
        (DocPage.LAST, "Last"),
    )
