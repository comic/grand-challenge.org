from django import forms
from django.contrib.auth import get_user_model
from django_select2.forms import Select2Widget

from grandchallenge.blogs.models import Post
from grandchallenge.core.forms import SaveFormInitMixin


class PostForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["authors"].queryset = get_user_model().objects.filter(
            pk=user.pk
        )
        self.fields["authors"].initial = [user]

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
            "tags": Select2Widget,
            "authors": forms.MultipleHiddenInput,
        }
