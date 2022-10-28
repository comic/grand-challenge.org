from actstream.models import Follow
from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from grandchallenge.notifications.models import (
    FollowGroupObjectPermission,
    FollowUserObjectPermission,
    Notification,
    NotificationGroupObjectPermission,
    NotificationUserObjectPermission,
)


class FollowAdmin(GuardedModelAdmin):
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


class NotificationAdmin(GuardedModelAdmin):
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
    list_filter = ("type", "read")
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
admin.site.register(FollowUserObjectPermission)
admin.site.register(FollowGroupObjectPermission)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(NotificationUserObjectPermission)
admin.site.register(NotificationGroupObjectPermission)
