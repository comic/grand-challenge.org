from django.contrib import admin

from grandchallenge.workspaces.models import (
    WorkbenchToken,
    Workspace,
    WorkspaceType,
    WorkspaceTypeConfiguration,
)

admin.site.register(WorkbenchToken)
admin.site.register(Workspace)
admin.site.register(WorkspaceType)
admin.site.register(WorkspaceTypeConfiguration)
