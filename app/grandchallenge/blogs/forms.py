from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django_select2.forms import Select2MultipleWidget
from guardian.utils import get_anonymous_user

from config import settings
from grandchallenge.blogs.models import Post
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorWidget


class PostForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, authors, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["authors"].queryset = (
            get_user_model()
            .objects.filter(
                groups=Group.objects.get(
                    name=settings.REGISTERED_USERS_GROUP_NAME
                )
            )
            .all()
            .order_by("username")
        )
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
        )
        widgets = {
            "tags": Select2MultipleWidget,
            "authors": Select2MultipleWidget,
        }


class PostUpdateForm(PostForm):
    class Meta(PostForm.Meta):
        fields = (*PostForm.Meta.fields, "published", "content")
        widgets = {
            **PostForm.Meta.widgets,
            "content": MarkdownEditorWidget,
        }
