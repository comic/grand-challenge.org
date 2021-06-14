from actstream.models import Action
from django.conf import settings
from django.db import models
from guardian.shortcuts import assign_perm

from grandchallenge.core.models import UUIDModel


class Notification(UUIDModel):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        help_text="Which user does this notification correspond to?",
        on_delete=models.CASCADE,
    )

    action = models.ForeignKey(
        Action,
        help_text="Which action is associated with this notification?",
        on_delete=models.CASCADE,
    )

    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user}"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self._assign_permissions()

    def _assign_permissions(self):
        assign_perm("view_notification", self.user, self)
        assign_perm("delete_notification", self.user, self)
        assign_perm("change_notification", self.user, self)
