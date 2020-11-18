from django.contrib import admin
from django.contrib.admin import ModelAdmin
from simple_history.admin import SimpleHistoryAdmin

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
    ]
    search_fields = [
        "creator__username",
        "workstation_image__workstation__title",
    ]


class WorkstationImageAdmin(ModelAdmin):
    exclude = ("image",)


admin.site.register(Workstation)
admin.site.register(WorkstationImage, WorkstationImageAdmin)
admin.site.register(Session, SessionHistoryAdmin)
