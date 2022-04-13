from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from grandchallenge.pages.models import Page


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


admin.site.register(Page, PageAdmin)
