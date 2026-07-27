from actstream.models import Follow
from django.contrib import admin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.notifications.models import (
    FollowGroupObjectPermission,
    FollowUserObjectPermission,
    Notification,
    NotificationGroupObjectPermission,
    NotificationUserObjectPermission,
)


class MissingRequiredObjectsFilter(admin.SimpleListFilter):
    title = "missing required objects"
    parameter_name = "objects_missing"

    def lookups(self, request, model_admin):
        return [
            ("1", "Yes"),
        ]

    def queryset(self, request, queryset):
        if self.value() != "1":
            return queryset

        pks = [
            notification.pk
            for notification in queryset.iterator()
            if not notification._required_objects_exist
        ]
        return queryset.filter(pk__in=pks)


class FollowAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "user",
        "follow_object",
        "content_type",
        "flag",
        "actor_only",
        "started",
    )
    raw_id_fields = ("user", "content_type")
    list_select_related = ("user", "content_type")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    readonly_fields = ("user",)
    ordering = ("-created",)
    list_display = (
        "__str__",
        "type",
        "actor",
        "message",
        "action_object",
        "target",
        "read",
    )
    list_filter = ("type", "read", MissingRequiredObjectsFilter)
    raw_id_fields = (
        "actor_content_type",
        "target_content_type",
        "action_object_content_type",
    )
    search_fields = ("user__username",)
    list_select_related = (
        "user",
        "actor_content_type",
        "target_content_type",
        "action_object_content_type",
    )


admin.site.unregister(Follow)
admin.site.register(Follow, FollowAdmin)
admin.site.register(FollowUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(FollowGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(
    NotificationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    NotificationGroupObjectPermission, GroupObjectPermissionAdmin
)
