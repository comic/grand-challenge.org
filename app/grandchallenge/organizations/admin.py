from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.organizations.models import (
    Organization,
    OrganizationGroupObjectPermission,
    OrganizationUserObjectPermission,
)

admin.site.register(Organization, GuardedModelAdmin)
admin.site.register(
    OrganizationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    OrganizationGroupObjectPermission, GroupObjectPermissionAdmin
)
