from django.contrib.auth import get_user_model
from django.db import models
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from grandchallenge.core.models import UUIDModel


class Conversation(UUIDModel):
    participants = models.ManyToManyField(
        get_user_model(),
        related_name="conversations",
        through="ConversationUser",
    )


class ConversationUser(models.Model):
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)


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
        through="DirectMessageUser",
    )

    is_reported_as_spam = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    message = models.TextField()


class DirectMessageUser(models.Model):
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    direct_message = models.ForeignKey(DirectMessage, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)


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
