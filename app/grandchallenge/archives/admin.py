from django.contrib import admin

from grandchallenge.archives.models import (
    Archive,
    ArchiveGroupObjectPermission,
    ArchiveItem,
    ArchiveItemGroupObjectPermission,
    ArchiveItemUserObjectPermission,
    ArchivePermissionRequest,
    ArchiveUserObjectPermission,
)
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    search_fields = ("title", "slug")
    list_display = ("pk", "title", "slug", "public", "workstation")
    list_filter = ("public", "workstation__slug")


@admin.register(ArchiveItem)
class ArchiveItemAdmin(admin.ModelAdmin):
    search_fields = ("archive__slug", "archive__title", "values__image__name")
    list_filter = ("archive__slug",)
    list_display = ("pk", "archive")
    list_select_related = ("archive",)
    readonly_fields = ("values",)


@admin.register(ArchivePermissionRequest)
class ArchivePermissionRequestAdmin(admin.ModelAdmin):
    readonly_fields = ("user", "archive")


admin.site.register(ArchiveUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(ArchiveGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(ArchiveItemUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    ArchiveItemGroupObjectPermission, GroupObjectPermissionAdmin
)
