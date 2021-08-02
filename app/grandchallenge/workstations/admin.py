from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from grandchallenge.components.admin import ComponentImageAdmin
from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)


class SessionHistoryAdmin(SimpleHistoryAdmin):
    ordering = ("-created",)
    list_display = [
        "pk",
        "created",
        "maximum_duration",
        "status",
        "creator",
        "region",
        "ping_times",
    ]
    list_filter = ["status", "region"]
    readonly_fields = [
        "creator",
        "workstation_image",
        "status",
        "logs",
        "region",
        "ping_times",
        "auth_token",
    ]
    search_fields = [
        "creator__username",
        "workstation_image__workstation__title",
    ]


admin.site.register(Workstation)
admin.site.register(WorkstationImage, ComponentImageAdmin)
admin.site.register(Session, SessionHistoryAdmin)
