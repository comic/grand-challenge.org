from django.contrib import admin

from grandchallenge.workstation_configs.models import (
    WorkstationConfig,
    WindowPreset,
)

admin.site.register(WorkstationConfig)
admin.site.register(WindowPreset)
