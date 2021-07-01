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


admin.site.unregister(Follow)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Notification, NotificationAdmin)
