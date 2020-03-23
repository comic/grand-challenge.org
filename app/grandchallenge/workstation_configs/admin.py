from django.contrib import admin

from grandchallenge.workstation_configs.models import (
    LookUpTable,
    WindowPreset,
    WorkstationConfig,
)


class WorkstationConfigAdmin(admin.ModelAdmin):
    readonly_fields = ("creator",)


admin.site.register(WorkstationConfig, WorkstationConfigAdmin)
admin.site.register(WindowPreset)
admin.site.register(LookUpTable)
