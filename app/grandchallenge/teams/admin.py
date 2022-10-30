from django.contrib import admin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.teams.models import (
    TeamGroupObjectPermission,
    TeamUserObjectPermission,
)

admin.site.register(TeamUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(TeamGroupObjectPermission, GroupObjectPermissionAdmin)
