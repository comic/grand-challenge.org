from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.forms import ModelForm

from grandchallenge.blogs.models import (
    Post,
    PostGroupObjectPermission,
    PostUserObjectPermission,
    Tag,
)
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.core.widgets import MarkdownEditorAdminWidget


class AdminPostForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ["authors"]:
            self.fields[field].widget.can_add_related = False

    class Meta:
        model = Post
        widgets = {"content": MarkdownEditorAdminWidget}
        exclude = ()


@admin.register(Post)
class PostAdmin(ModelAdmin):
    form = AdminPostForm
    list_display = ("pk", "slug", "title", "published", "highlight")
    list_filter = ("tags", "highlight")
    autocomplete_fields = ("authors",)


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("__str__", "slug")


admin.site.register(PostUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(PostGroupObjectPermission, GroupObjectPermissionAdmin)
