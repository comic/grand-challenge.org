from actstream.models import Follow
from django.contrib import admin
from django.contrib.admin import ModelAdmin


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


admin.site.unregister(Follow)
admin.site.register(Follow, FollowAdmin)
