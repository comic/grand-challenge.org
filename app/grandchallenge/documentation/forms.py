from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from grandchallenge.core.widgets import MarkdownEditorInlineWidget
from grandchallenge.documentation.models import DocPage


class DocPageCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = DocPage
        fields = ("title", "content", "parent")
        widgets = {"content": MarkdownEditorInlineWidget}


class DocPageUpdateForm(DocPageCreateForm):
    """Like the create form but you can also move the page."""

    position = forms.IntegerField()
    position.label = "Move to index position"
    position.required = False
