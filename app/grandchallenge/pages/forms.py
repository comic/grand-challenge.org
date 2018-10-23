from ckeditor_uploader.widgets import CKEditorUploadingWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import BLANK_CHOICE_DASH
from django.utils.translation import gettext

from grandchallenge.core.urlresolvers import reverse
from grandchallenge.pages.models import Page


class PageCreateForm(forms.ModelForm):
    html = forms.CharField(widget=CKEditorUploadingWidget())

    def __init__(self, *args, **kwargs):
        self.challenge = kwargs.pop("challenge", None)
        super().__init__(*args, **kwargs)
        if self.challenge is not None and "html" in self.fields:
            self.fields["html"].widget.config.update(
                {
                    "filebrowserUploadUrl": reverse(
                        "uploads:ck-create",
                        kwargs={
                            "challenge_short_name": self.challenge.short_name
                        },
                    ),
                    "filebrowserBrowseUrl": reverse(
                        "uploads:ck-browse",
                        kwargs={
                            "challenge_short_name": self.challenge.short_name
                        },
                    ),
                }
            )

            if self.challenge.allow_unfiltered_page_html:
                # See https://github.com/django-ckeditor/django-ckeditor#if-you-want-to-use-allowedcontent
                self.fields["html"].widget.config.update(
                    {
                        "allowedContent": True,
                        "removePlugins": "stylesheetparser",
                    }
                )

        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    def clean_title(self):
        """ Ensure that page titles are not duplicated for a challenge """
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
        fields = ("title", "permission_lvl", "display_title", "hidden", "html")


class PageUpdateForm(PageCreateForm):
    """ Like the page update form but you can also move the page """

    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices = (
        (BLANK_CHOICE_DASH[0]),
        (Page.FIRST, "First"),
        (Page.UP, "Up"),
        (Page.DOWN, "Down"),
        (Page.LAST, "Last"),
    )
