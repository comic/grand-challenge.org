from actstream.models import Action
from django.conf import settings
from django.db import models
from guardian.shortcuts import assign_perm


class Notification(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        help_text="which user does this notification correspond to?",
        on_delete=models.CASCADE,
    )

    action = models.ForeignKey(
        Action,
        help_text="which actions is associated with this notification?",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"Notification for {self.user}"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self._assign_permissions()

    def _assign_permissions(self):
        assign_perm("change_notification", self.user, self)
        assign_perm("view_notification", self.user, self)
        assign_perm("delete_notification", self.user, self)

    @property
    def read(self):
        last_read = self.user.user_profile.notifications_last_read_at
        return last_read is not None and last_read > self.action.timestamp
