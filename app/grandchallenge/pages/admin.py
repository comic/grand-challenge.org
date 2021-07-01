from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from grandchallenge.pages.models import Page


class PageAdmin(SimpleHistoryAdmin):
    list_filter = ("challenge", "permission_level", "hidden")
    list_display = ("title", "challenge", "permission_level", "hidden")
    search_fields = ("html",)


admin.site.register(Page, PageAdmin)
