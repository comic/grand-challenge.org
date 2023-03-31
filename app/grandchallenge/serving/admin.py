from django.contrib import admin

from grandchallenge.serving.models import Download


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    ordering = ("-modified",)
    list_display = ("modified", "count", "creator", "image", "submission")
    search_fields = ("creator__username", "image__pk", "submission__pk")
    readonly_fields = ("creator", "image", "submission", "count")
