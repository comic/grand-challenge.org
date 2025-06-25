from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorFullPageWidget
from grandchallenge.documentation.models import DocPage


class DocPageCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = DocPage
        fields = ("title", "parent", "is_faq")


class DocPageMetadataUpdateForm(DocPageCreateForm):
    """Like the create form, but you can also move the page."""

    position = forms.IntegerField()
    position.label = "Move to index position"
    position.required = False


class DocPageContentUpdateForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = DocPage
        fields = ("content",)
        widgets = {
            "content": MarkdownEditorFullPageWidget,
        }
