from django import forms
from django.core.exceptions import ValidationError
from django.db.models import BLANK_CHOICE_DASH
from django_summernote.widgets import SummernoteInplaceWidget

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.pages.models import Page


class PageCreateForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.uses_markdown:
            del self.fields["html"]
        else:
            del self.fields["content_markdown"]

    class Meta:
        model = Page
        fields = (
            "display_title",
            "permission_level",
            "hidden",
            "html",
            "content_markdown",
        )
        widgets = {
            "html": SummernoteInplaceWidget(),
            "content_markdown": MarkdownEditorWidget,
        }
        help_texts = {
            "html": (
                "The content of your page. <b>Please note</b>: your html will "
                "be filtered after it has been saved to remove any non-HTML5 "
                "compliant markup and scripts. The filtering is not reflected "
                "in the live view so please <b>check the rendering of your "
                "page after you click save</b>. If you're going to paste from "
                "another source such as MS Word, please <b>paste without "
                "formatting</b> using <b>CTRL+SHIFT+V</b> on Windows or "
                "<b>⇧+⌥+⌘+V</b> on OS X."
            )
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
