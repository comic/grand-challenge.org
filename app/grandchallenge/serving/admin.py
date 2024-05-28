from django.contrib import admin

from grandchallenge.serving.models import Download


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    list_display = (
        "created",
        "creator",
        "image",
        "submission",
        "component_interface_value",
        "challenge_request",
        "feedback",
    )
    search_fields = (
        "creator__username",
        "image__pk",
        "submission__pk",
        "component_interface_value__pk",
        "challenge_request__pk",
        "feedback__pk",
    )
    readonly_fields = (
        "creator",
        "image",
        "submission",
        "component_interface_value",
        "challenge_request",
        "feedback",
    )
