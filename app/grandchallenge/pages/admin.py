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
from grandchallenge.pages.views import html2md


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
        "content_markdown",
    )
    actions = ("convert_markdown",)

    @admin.action(description="Convert markdown", permissions=["change"])
    def convert_markdown(self, request, queryset):
        for page in queryset.filter(uses_markdown=True):
            page.content_markdown = html2md(html=page.html)
            page.save()


admin.site.register(PageUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(PageGroupObjectPermission, GroupObjectPermissionAdmin)
