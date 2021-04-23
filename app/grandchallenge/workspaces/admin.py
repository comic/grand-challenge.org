from django.contrib import admin

from grandchallenge.workspaces.models import (
    WorkbenchToken,
    Workspace,
    WorkspaceTypeConfiguration,
)

admin.site.register(WorkbenchToken)
admin.site.register(Workspace)
admin.site.register(WorkspaceTypeConfiguration)
