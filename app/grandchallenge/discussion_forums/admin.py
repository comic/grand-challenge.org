from django.contrib import admin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.discussion_forums.models import (
    Forum,
    ForumGroupObjectPermission,
    ForumPost,
    ForumPostGroupObjectPermission,
    ForumPostUserObjectPermission,
    ForumTopic,
    ForumTopicGroupObjectPermission,
    ForumTopicUserObjectPermission,
    ForumUserObjectPermission,
    TopicReadRecord,
)


@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ("id", "parent_object")
    readonly_fields = ("parent_object", "source_object", "created", "modified")

    def parent_object(self, obj):
        return obj.parent_object


@admin.register(ForumTopic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("subject", "linked_forum", "kind", "creator", "created")
    search_fields = ("subject", "creator__username")
    list_filter = ("kind",)
    readonly_fields = (
        "created",
        "modified",
        "source_object",
        "forum",
        "creator",
        "last_post",
        "last_post_on",
    )

    def linked_forum(self, obj):
        return f"Forum for {obj.forum.parent_object}"


@admin.register(ForumPost)
class PostAdmin(admin.ModelAdmin):
    list_display = ("topic", "creator", "created")
    search_fields = ("creator__username",)
    readonly_fields = (
        "created",
        "modified",
        "source_object",
        "topic",
        "creator",
    )


@admin.register(TopicReadRecord)
class TopicReadRecordAdmin(admin.ModelAdmin):
    readonly_fields = ("topic", "user", "source_object", "created", "modified")


admin.site.register(ForumUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(ForumGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(ForumTopicUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(
    ForumTopicGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(ForumPostUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(ForumPostGroupObjectPermission, GroupObjectPermissionAdmin)
