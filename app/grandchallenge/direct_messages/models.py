from django.contrib.auth import get_user_model
from django.db import models
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


class Conversation(UUIDModel):
    participants = models.ManyToManyField(
        get_user_model(),
        related_name="conversations",
        through="ConversationParticipant",
    )

    def get_absolute_url(self):
        return reverse(
            "direct-messages:conversation-detail", kwargs={"pk": self.pk}
        )

    class Meta:
        permissions = (
            (
                "create_conversation_direct_message",
                "Create a Direct Message for a Conversation",
            ),
            (
                "mark_conversation_read",
                "Mark a Conversation as read",
            ),
        )


class ConversationParticipant(models.Model):
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    participant = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)


class ConversationUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Conversation, on_delete=models.CASCADE)


class ConversationGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Conversation, on_delete=models.CASCADE)


class DirectMessage(UUIDModel):
    conversation = models.ForeignKey(
        Conversation,
        related_name="direct_messages",
        null=False,
        on_delete=models.CASCADE,
    )
    sender = models.ForeignKey(
        get_user_model(),
        related_name="sent_direct_messages",
        null=True,
        on_delete=models.SET_NULL,
    )
    unread_by = models.ManyToManyField(
        get_user_model(),
        related_name="unread_direct_messages",
        through="DirectMessageUnreadBy",
    )

    is_reported_as_spam = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    message = models.TextField()

    def get_absolute_url(self):
        return reverse(
            "direct-messages:conversation-detail",
            kwargs={"pk": self.conversation.pk},
        )


class DirectMessageUnreadBy(models.Model):
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    direct_message = models.ForeignKey(DirectMessage, on_delete=models.CASCADE)
    unread_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)


class Mute(UUIDModel):
    target = models.ForeignKey(
        get_user_model(),
        related_name="muted_by_users",
        on_delete=models.CASCADE,
        help_text="The user who has been muted",
    )
    source = models.ForeignKey(
        get_user_model(),
        related_name="muted_users",
        on_delete=models.CASCADE,
        help_text="The user who has muted the target",
    )
