from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.uploads.models import (
    UserUpload,
    UserUploadGroupObjectPermission,
    UserUploadUserObjectPermission,
)


@admin.register(UserUpload)
class UserUploadAdmin(GuardedModelAdmin):
    list_display = ("pk", "created", "creator", "filename", "status")
    list_filter = ("status",)
    ordering = ("-created",)
    search_fields = ("pk", "creator__username", "filename", "s3_upload_id")
    readonly_fields = ("creator", "status", "s3_upload_id")


admin.site.register(UserUploadUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    UserUploadGroupObjectPermission, GroupObjectPermissionAdmin
)
