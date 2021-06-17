from django.contrib import admin

from grandchallenge.archives.models import (
    Archive,
    ArchiveItem,
    ArchivePermissionRequest,
)


class ArchiveAdmin(admin.ModelAdmin):
    search_fields = (
        "title",
        "slug",
    )
    list_display = (
        "pk",
        "title",
        "slug",
        "public",
    )
    list_filter = ("public",)


class ArchiveItemAdmin(admin.ModelAdmin):
    search_fields = (
        "archive__slug",
        "archive__title",
        "values__image__name",
    )
    list_filter = ("archive__slug",)
    list_display = (
        "pk",
        "archive",
    )
    list_select_related = ("archive",)
    readonly_fields = ("values",)


class ArchivePermissionRequestAdmin(admin.ModelAdmin):
    readonly_fields = (
        "user",
        "archive",
    )


admin.site.register(Archive, ArchiveAdmin)
admin.site.register(ArchiveItem, ArchiveItemAdmin)
admin.site.register(ArchivePermissionRequest, ArchivePermissionRequestAdmin)
