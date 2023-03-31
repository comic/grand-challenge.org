from django.contrib import admin
from django.contrib.admin import ModelAdmin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.hanging_protocols.models import (
    HangingProtocol,
    HangingProtocolGroupObjectPermission,
    HangingProtocolUserObjectPermission,
)


@admin.register(HangingProtocol)
class HangingProtocolAdmin(ModelAdmin):
    readonly_fields = ("creator",)


admin.site.register(
    HangingProtocolUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    HangingProtocolGroupObjectPermission, GroupObjectPermissionAdmin
)
