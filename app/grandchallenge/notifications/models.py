from actstream.models import user_stream
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )

    receive_notification_emails = models.BooleanField(
        default=True,
        help_text="Whether to receive email updates about notifications",
    )
    email_last_sent_at = models.DateTimeField(
        default=None, null=True, editable=False
    )

    has_notifications = models.BooleanField(default=False, editable=False)
    notifications_last_read_at = models.DateTimeField(
        auto_now_add=True, editable=False
    )

    def __str__(self):
        return f"{self.user}"

    @property
    def notifications(self):
        notifications = user_stream(obj=self.user)

        # Workaround for
        # https://github.com/justquick/django-activity-stream/issues/482
        notifications = notifications.exclude(
            actor_content_type=ContentType.objects.get_for_model(self.user),
            actor_object_id=self.user.pk,
        )

        return notifications
