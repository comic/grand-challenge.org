from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)


class SessionHistoryAdmin(SimpleHistoryAdmin):
    list_display = ["pk", "created", "status", "creator"]
    list_filter = ["status"]
    readonly_fields = ["creator", "workstation_image", "status", "logs"]


admin.site.register(Workstation)
admin.site.register(WorkstationImage)
admin.site.register(Session, SessionHistoryAdmin)
