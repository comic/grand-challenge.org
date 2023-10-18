from django.contrib.auth import get_user_model
from django.db import models

from grandchallenge.core.models import UUIDModel


class DirectMessage(UUIDModel):
    sender = models.ForeignKey(
        get_user_model(),
        related_name="sent_direct_messages",
        null=True,
        on_delete=models.SET_NULL,
    )
    receiver = models.ForeignKey(
        get_user_model(),
        related_name="received_direct_messages",
        null=True,
        on_delete=models.SET_NULL,
    )

    is_read_by_receiver = models.BooleanField(default=False)
    is_reported_as_spam = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    message = models.TextField()


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
