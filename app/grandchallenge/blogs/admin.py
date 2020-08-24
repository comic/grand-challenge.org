from django.contrib import admin
from django.forms import ModelForm
from markdownx.admin import MarkdownxModelAdmin

from grandchallenge.blogs.models import Post
from grandchallenge.core.widgets import MarkdownEditorAdminWidget


class PostForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in [
            "authors",
        ]:
            self.fields[field].widget.can_add_related = False

    class Meta:
        model = Post
        widgets = {
            "content": MarkdownEditorAdminWidget,
        }
        exclude = ()


class PostAdmin(MarkdownxModelAdmin):
    form = PostForm
    list_display = (
        "pk",
        "title",
        "published",
    )
    autocomplete_fields = ("authors",)


admin.site.register(Post, PostAdmin)
