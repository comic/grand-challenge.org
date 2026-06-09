from django.contrib import admin

from grandchallenge.broken_links.models import BrokenLink


@admin.register(BrokenLink)
class BrokenLinkAdmin(admin.ModelAdmin):
    list_display = ("path", "domain", "referer", "is_internal", "created")
    list_filter = ("is_internal",)
    search_fields = ("path", "referer", "domain")
    readonly_fields = (
        "created",
        "domain",
        "path",
        "referer",
        "user_agent",
        "ip_address",
        "is_internal",
    )
    ordering = ("-created",)
