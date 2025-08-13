from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.db import models
from django.db.models import (
    BooleanField,
    Case,
    Count,
    Prefetch,
    Q,
    Value,
    When,
)
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.profiles.models import NotificationEmailOptions
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
            self.unread_by.clear()

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

    class Meta:
        unique_together = (("direct_message", "unread_by"),)


@receiver(m2m_changed, sender=DirectMessageUnreadBy)
def email_subscribed_users_about_new_message(
    sender, instance, action, reverse, model, pk_set, **_
):
    if action != "post_add" or reverse:
        return

    site = Site.objects.get_current()

    for user in (
        instance.unread_by.select_related("user_profile")
        .filter(
            user_profile__notification_email_choice=NotificationEmailOptions.INSTANT
        )
        .all()
    ):
        user.user_profile.dispatch_unread_direct_messages_email(
            site=site,
            new_unread_message_count=1,
            new_senders=[instance.sender],
        )


class DirectMessageUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"delete_directmessage"})

    content_object = models.ForeignKey(DirectMessage, on_delete=models.CASCADE)


class DirectMessageGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(DirectMessage, on_delete=models.CASCADE)


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

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()
            DirectMessageUnreadBy.objects.filter(
                direct_message__sender=self.target, unread_by=self.source
            ).delete()

    def assign_permissions(self):
        assign_perm("delete_mute", self.source, self)

    class Meta:
        unique_together = (("target", "source"),)


class MuteUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"delete_mute"})

    content_object = models.ForeignKey(Mute, on_delete=models.CASCADE)


class MuteGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Mute, on_delete=models.CASCADE)


class ConversationQuerySet(models.QuerySet):
    def with_most_recent_message(self, *, user):
        """
        Adds the most recent message to each conversation

        Also includes a count of the number of unread messages in that conversation,
        and whether the conversation has unread messages which can be used for
        ordering.
        """
        return self.prefetch_related(
            "participants__user_profile",
            Prefetch(
                "direct_messages",
                queryset=DirectMessage.objects.order_by(
                    "-created"
                ).select_related("sender"),
            ),
        ).annotate(
            most_recent_message_created=models.Max("direct_messages__created"),
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

    def with_unread_by_user(self, *, user):
        """Adds whether the user has read each direct message in the conversation"""
        return self.prefetch_related(
            Prefetch(
                "direct_messages",
                queryset=DirectMessage.objects.order_by("created")
                .annotate(
                    unread_by_user=Case(
                        When(unread_by=user, then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField(),
                    )
                )
                .distinct(),
            )
        )

    def for_participants(self, *, participants):
        """
        Find the conversations with the given set of participants

        Looks for set equality. If there are additional or missing participants
        those conversations are excluded.
        """
        return self.annotate(
            total_participants_count=Count("participants", distinct=True),
            relevant_participants_count=Count(
                "participants",
                filter=Q(participants__in=participants),
                distinct=True,
            ),
        ).filter(
            total_participants_count=len(participants),
            relevant_participants_count=len(participants),
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

    @property
    def list_view_url(self):
        url = reverse("direct_messages:conversation-list")
        query = urlencode(query={"conversation": self.pk})
        return f"{url}?{query}"

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

    class Meta:
        unique_together = (("conversation", "participant"),)


class ConversationUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset(
        {
            "create_conversation_direct_message",
            "mark_conversation_read",
            "view_conversation",
            "mark_conversation_message_as_spam",
        }
    )

    content_object = models.ForeignKey(Conversation, on_delete=models.CASCADE)


class ConversationGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Conversation, on_delete=models.CASCADE)
