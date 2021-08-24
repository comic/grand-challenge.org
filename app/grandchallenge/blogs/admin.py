from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.forms import ModelForm
from markdownx.admin import MarkdownxModelAdmin

from grandchallenge.blogs.models import Post, Tag
from grandchallenge.core.widgets import MarkdownEditorAdminWidget


class AdminPostForm(ModelForm):
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
    form = AdminPostForm
    list_display = (
        "pk",
        "title",
        "published",
    )
    list_filter = ("tags", "companies")
    autocomplete_fields = ("authors",)


class TagAdmin(ModelAdmin):
    list_display = (
        "__str__",
        "slug",
    )


admin.site.register(Post, PostAdmin)
admin.site.register(Tag, TagAdmin)
