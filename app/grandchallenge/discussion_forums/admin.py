from django.contrib import admin

from grandchallenge.discussion_forums.models import Forum, Post, Topic


@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ("id", "parent_object")

    def parent_object(self, obj):
        return obj.get_parent()


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("subject", "forum", "type", "creator")
    search_fields = ("subject", "creator__username")
    list_filter = ("type", "forum__slug")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("subject", "topic", "creator")
    search_fields = ("subject", "creator__username")
