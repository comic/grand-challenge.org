from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage

from grandchallenge.core.widgets import MarkdownEditorAdminWidget


class MarkdownFlatPageForm(FlatpageForm):
    class Meta(FlatpageForm.Meta):
        widgets = {"content": MarkdownEditorAdminWidget()}


class MarkdownFlatPageAdmin(FlatPageAdmin):
    form = MarkdownFlatPageForm


class UserObjectPermissionAdmin(admin.ModelAdmin):
    readonly_fields = ("user", "permission", "content_object")
    search_fields = ("user__username", "content_object__pk")
    list_display = ("user", "permission", "content_object")


class GroupObjectPermissionAdmin(admin.ModelAdmin):
    readonly_fields = ("group", "permission", "content_object")
    search_fields = ("group__name", "content_object__pk")
    list_display = ("group", "permission", "content_object")


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, MarkdownFlatPageAdmin)
