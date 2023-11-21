from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.direct_messages.models import (
    Conversation,
    DirectMessageUnreadBy,
)


@receiver(m2m_changed, sender=Conversation.participants.through)
def update_permissions_on_participants_changed(
    instance, action, reverse, pk_set, **_
):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        users = [instance]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            conversations = instance.conversations.all()
        else:
            conversations = Conversation.objects.filter(pk__in=pk_set)
    else:
        conversations = Conversation.objects.filter(pk=instance.pk)
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            users = instance.participants.all()
        else:
            users = get_user_model().objects.filter(pk__in=pk_set)

    if "add" in action:
        op = assign_perm
    else:
        op = remove_perm
        DirectMessageUnreadBy.objects.filter(
            direct_message__conversation__in=conversations, unread_by__in=users
        ).delete()

    for user in users:
        if user.username == settings.ANONYMOUS_USER_NAME:
            raise RuntimeError(
                "The Anonymous User cannot be added to this group"
            )

        op("view_conversation", user, conversations)
        op("create_conversation_direct_message", user, conversations)
        op("mark_conversation_read", user, conversations)
        op("mark_conversation_message_as_spam", user, conversations)
