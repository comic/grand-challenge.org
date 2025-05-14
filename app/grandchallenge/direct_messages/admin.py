from django.contrib import admin

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.direct_messages.models import (
    Conversation,
    ConversationGroupObjectPermission,
    ConversationUserObjectPermission,
    DirectMessage,
    DirectMessageGroupObjectPermission,
    DirectMessageUserObjectPermission,
    Mute,
    MuteGroupObjectPermission,
    MuteUserObjectPermission,
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "participant_usernames",
    )
    readonly_fields = ("participant_usernames",)
    search_fields = (
        "pk",
        "participants__username",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("participants")

    def participant_usernames(self, obj):
        return ", ".join(user.username for user in obj.participants.all())


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "created",
        "sender",
        "unread_by_usernames",
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
    ordering = ("-created",)
    search_fields = (
        "pk",
        "sender__username",
        "conversation__pk",
        "unread_by__username",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("unread_by")

    def unread_by_usernames(self, obj):
        return ", ".join(user.username for user in obj.unread_by.all())


@admin.register(Mute)
class MuteAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "source",
        "target",
    )
    readonly_fields = (
        "source",
        "target",
    )
    search_fields = (
        "source__username",
        "target__username",
    )


admin.site.register(
    ConversationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    ConversationGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(
    DirectMessageUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    DirectMessageGroupObjectPermission, GroupObjectPermissionAdmin
)
admin.site.register(MuteUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(MuteGroupObjectPermission, GroupObjectPermissionAdmin)
