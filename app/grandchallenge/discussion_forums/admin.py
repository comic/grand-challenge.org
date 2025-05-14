from django.contrib import admin

from grandchallenge.discussion_forums.models import Forum, Post, Topic


@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ("id", "parent_object")
    readonly_fields = ("parent_object",)

    def parent_object(self, obj):
        return obj.parent_object


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("subject", "linked_forum", "kind", "creator")
    search_fields = ("subject", "creator__username")
    list_filter = ("kind",)

    def linked_forum(self, obj):
        return f"Forum for {obj.forum.parent_object}"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("subject", "topic", "creator")
    search_fields = ("subject", "creator__username")
