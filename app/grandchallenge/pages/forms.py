from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import BLANK_CHOICE_DASH
from django.utils.translation import gettext
from django_summernote.widgets import SummernoteInplaceWidget

from grandchallenge.pages.models import Page


class PageCreateForm(forms.ModelForm):
    def __init__(self, *args, challenge, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge = challenge
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    def clean_title(self):
        """Ensure that page titles are not duplicated for a challenge."""
        title = self.cleaned_data["title"]
        queryset = Page.objects.filter(
            challenge=self.challenge, title__iexact=title
        )

        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError(
                gettext(
                    "A page with that title already exists for this challenge"
                ),
                code="duplicate",
            )

        return title

    class Meta:
        model = Page
        fields = (
            "title",
            "permission_level",
            "display_title",
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
