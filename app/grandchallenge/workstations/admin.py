from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)

admin.site.register(Workstation)
admin.site.register(WorkstationImage)
admin.site.register(Session, SimpleHistoryAdmin)
