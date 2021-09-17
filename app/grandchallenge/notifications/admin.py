from actstream.models import Follow
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from grandchallenge.notifications.models import Notification


class FollowAdmin(ModelAdmin):
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


class NotificationAdmin(ModelAdmin):
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


admin.site.unregister(Follow)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Notification, NotificationAdmin)
