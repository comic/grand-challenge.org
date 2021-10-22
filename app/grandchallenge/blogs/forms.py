from django import forms
from django.core.exceptions import ValidationError
from django_select2.forms import Select2MultipleWidget
from guardian.utils import get_anonymous_user

from grandchallenge.blogs.models import Post
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.groups.forms import UserGroupForm


class PostForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, authors, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["authors"].queryset = authors
        self.fields["authors"].initial = authors

        self.fields["tags"].required = True

    def clean_authors(self):
        authors = self.cleaned_data["authors"]
        if get_anonymous_user() in authors:
            raise ValidationError("You cannot add this user!")
        return authors

    class Meta:
        model = Post
        fields = (
            "title",
            "description",
            "logo",
            "authors",
            "tags",
            "highlight",
        )
        widgets = {
            "tags": Select2MultipleWidget,
            "authors": forms.MultipleHiddenInput,
        }


class PostUpdateForm(PostForm):
    class Meta(PostForm.Meta):
        fields = (*PostForm.Meta.fields, "published", "content")
        widgets = {
            **PostForm.Meta.widgets,
            "content": MarkdownEditorWidget,
        }


class AuthorsForm(UserGroupForm):
    role = "author"
