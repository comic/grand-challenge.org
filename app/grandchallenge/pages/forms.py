from django import forms
from django.core.exceptions import ValidationError
from django.db.models import BLANK_CHOICE_DASH

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.pages.models import Page


class PageCreateForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = Page
        fields = (
            "display_title",
            "permission_level",
            "hidden",
            "content_markdown",
        )
        widgets = {
            "content_markdown": MarkdownEditorWidget,
        }

    def clean_display_title(self):
        display_title = self.cleaned_data["display_title"]

        if display_title.lower() in {"evaluation"}:
            # evaluation results in a URL clash, especially with the update page.
            raise ValidationError(
                "Title not allowed, please select an alternative"
            )

        return display_title


class PageUpdateForm(PageCreateForm):
    """Like the page update form but you can also move the page."""

    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices = (
        (BLANK_CHOICE_DASH[0]),
        (Page.FIRST, "First"),
        (Page.UP, "Up"),
        (Page.DOWN, "Down"),
        (Page.LAST, "Last"),
    )
