from django.contrib import admin

from grandchallenge.workspaces.models import (
    Token,
    Workspace,
    WorkspaceType,
    WorkspaceTypeConfiguration,
)

admin.site.register(Token)
admin.site.register(Workspace)
admin.site.register(WorkspaceType)
admin.site.register(WorkspaceTypeConfiguration)
