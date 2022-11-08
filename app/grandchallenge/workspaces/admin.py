from django.contrib import admin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.workspaces.models import (
    WorkbenchToken,
    Workspace,
    WorkspaceGroupObjectPermission,
    WorkspaceTypeConfiguration,
    WorkspaceUserObjectPermission,
)

admin.site.register(WorkbenchToken)
admin.site.register(Workspace)
admin.site.register(WorkspaceUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(WorkspaceGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(WorkspaceTypeConfiguration)
