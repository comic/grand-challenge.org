from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.pages.models import (
    Page,
    PageGroupObjectPermission,
    PageUserObjectPermission,
)


@admin.register(Page)
class PageAdmin(SimpleHistoryAdmin):
    list_filter = ("challenge", "permission_level", "hidden")
    list_display = (
        "slug",
        "display_title",
        "challenge",
        "permission_level",
        "hidden",
    )
    search_fields = (
        "slug",
        "display_title",
        "html",
    )


admin.site.register(PageUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(PageGroupObjectPermission, GroupObjectPermissionAdmin)
