from django.contrib import admin

from grandchallenge.browser_sessions.models import BrowserSession


@admin.register(BrowserSession)
class BrowserSessionAdmin(admin.ModelAdmin):
    list_display = ("session_key", "user", "created", "expire_date")
    search_fields = ("user__username",)
    readonly_fields = ("user", "session_key", "expire_date", "session_data")
    ordering = ("-expire_date",)
