from django.contrib import admin

from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
)


@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ("id", "parent_object")
    readonly_fields = ("parent_object",)

    def parent_object(self, obj):
        return obj.parent_object


@admin.register(ForumTopic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("subject", "linked_forum", "kind", "creator")
    search_fields = ("subject", "creator__username")
    list_filter = ("kind",)

    def linked_forum(self, obj):
        return f"Forum for {obj.forum.parent_object}"


@admin.register(ForumPost)
class PostAdmin(admin.ModelAdmin):
    list_display = ("topic", "creator")
    search_fields = ("creator__username",)
