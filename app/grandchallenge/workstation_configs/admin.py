from django.contrib import admin

from grandchallenge.workstation_configs.models import (
    LookUpTable,
    WindowPreset,
    WorkstationConfig,
)

admin.site.register(WorkstationConfig)
admin.site.register(WindowPreset)
admin.site.register(LookUpTable)
