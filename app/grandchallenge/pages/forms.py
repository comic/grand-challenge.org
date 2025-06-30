from django import forms
from django.db.models import BLANK_CHOICE_DASH

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorFullPageWidget
from grandchallenge.pages.models import Page


class PageCreateForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = Page
        fields = (
            "display_title",
            "permission_level",
            "hidden",
        )


class PageMetadataUpdateForm(PageCreateForm):
    """Like the page create form, but you can also move the page."""

    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices = (
        (BLANK_CHOICE_DASH[0]),
        (Page.FIRST, "First"),
        (Page.UP, "Up"),
        (Page.DOWN, "Down"),
        (Page.LAST, "Last"),
    )


class PageContentUpdateForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = Page
        fields = ("content_markdown",)
        widgets = {
            "content_markdown": MarkdownEditorFullPageWidget,
        }
