from django.contrib import admin

from grandchallenge.direct_messages.models import (
    Conversation,
    DirectMessage,
    Mute,
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "participant_usernames",
    )
    list_prefetch_related = ("participants",)
    readonly_fields = ("participant_usernames",)

    def participant_usernames(self, obj):
        return ", ".join(user.username for user in obj.participants.all())


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "conversation",
        "sender",
        "is_reported_as_spam",
        "is_deleted",
        "message",
    )
    readonly_fields = (
        "conversation",
        "sender",
        "message",
        "unread_by_usernames",
    )
    list_filter = (
        "is_reported_as_spam",
        "is_deleted",
    )

    def unread_by_usernames(self, obj):
        return ", ".join(user.username for user in obj.unread_by.all())


@admin.register(Mute)
class MuteAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "target",
    )
    readonly_fields = (
        "source",
        "target",
    )
