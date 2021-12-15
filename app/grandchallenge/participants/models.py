from actstream.actions import follow
from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.db import models

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import RequestBase
from grandchallenge.notifications.models import Notification, NotificationType


class RegistrationRequest(RequestBase):
    """
    When a user wants to join a project, admins have the option of reviewing
    each user before allowing or denying them. This class records the needed
    info for that.
    """

    challenge = models.ForeignKey(
        Challenge,
        help_text="To which project does the user want to register?",
        on_delete=models.CASCADE,
    )

    @property
    def base_object(self):
        return self.challenge

    @property
    def object_name(self):
        return self.challenge.short_name

    @property
    def add_method(self):
        return self.base_object.add_participant

    @property
    def remove_method(self):
        return self.base_object.remove_participant

    def __str__(self):
        return f"{self.challenge.short_name} registration request by user {self.user.username}"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding and self.challenge.require_participant_review:
            follow(
                user=self.user, obj=self, actor_only=False, send_action=False,
            )
            Notification.send(
                type=NotificationType.NotificationTypeChoices.ACCESS_REQUEST,
                message="requested access to",
                actor=self.user,
                target=self.base_object,
            )
        elif adding and not self.challenge.require_participant_review:
            # immediately allow access, no need for a notification
            self.status = self.ACCEPTED
            self.save()

    def delete(self):
        ct = ContentType.objects.filter(
            app_label=self._meta.app_label, model=self._meta.model_name
        ).get()
        Follow.objects.filter(object_id=self.pk, content_type=ct).delete()
        super().delete()

    class Meta:
        unique_together = (("challenge", "user"),)
