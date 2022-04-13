from django import forms
from django.db.models import BLANK_CHOICE_DASH
from django_summernote.widgets import SummernoteInplaceWidget

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.pages.models import Page


class PageCreateForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, challenge, **kwargs):
        self.challenge = challenge
        super().__init__(*args, **kwargs)

    class Meta:
        model = Page
        fields = (
            "display_title",
            "permission_level",
            "hidden",
            "html",
        )
        widgets = {"html": SummernoteInplaceWidget()}
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
