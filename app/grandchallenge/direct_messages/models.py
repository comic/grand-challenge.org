from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import (
    BooleanField,
    Case,
    Count,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm

from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


class DirectMessage(UUIDModel):
    conversation = models.ForeignKey(
        "Conversation",
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

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if self.is_deleted or self.is_reported_as_spam:
            DirectMessageUnreadBy.objects.filter(direct_message=self).delete()

        if adding:
            self.assign_permissions()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    def assign_permissions(self):
        assign_perm("delete_directmessage", self.sender, self)


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


class ConversationQuerySet(models.QuerySet):
    def with_most_recent_message(self, *, user):
        most_recent_message = DirectMessage.objects.order_by("-created")

        return self.prefetch_related(
            "participants__user_profile",
            Prefetch(
                "direct_messages",
                queryset=most_recent_message.select_related("sender"),
            ),
        ).annotate(
            most_recent_message_created=Subquery(
                most_recent_message.filter(conversation=OuterRef("pk")).values(
                    "created"
                )[:1]
            ),
            unread_message_count=Count(
                "direct_messages",
                filter=Q(direct_messages__unread_by=user),
            ),
            unread_by_user=Case(
                When(unread_message_count=0, then=Value(False)),
                default=Value(True),
                output_field=BooleanField(),
            ),
        )


class Conversation(UUIDModel):
    participants = models.ManyToManyField(
        get_user_model(),
        related_name="conversations",
        through="ConversationParticipant",
    )

    objects = ConversationQuerySet.as_manager()

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
            ("mark_conversation_read", "Mark a Conversation as read"),
            (
                "mark_conversation_message_as_spam",
                "Mark a Conversation Message as spam",
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
