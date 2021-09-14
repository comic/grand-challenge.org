from django.core.management import BaseCommand

from grandchallenge.notifications.models import Notification, NotificationType


class Command(BaseCommand):
    def handle(self, *args, **options):
        deleted_notification = 0
        for notification in Notification.objects.filter(
            type=NotificationType.NotificationTypeChoices.EVALUATION_STATUS
        ).all():
            if (
                notification.user
                not in notification.target.challenge.get_admins()
            ):
                if (
                    notification.actor
                    and notification.user == notification.actor
                ):
                    continue
                notification.delete()
                deleted_notification += 1

        for notification in Notification.objects.filter(
            type=NotificationType.NotificationTypeChoices.MISSING_METHOD
        ).all():
            if (
                notification.user
                not in notification.target.challenge.get_admins()
            ):
                notification.delete()
                deleted_notification += 1

        for notification in Notification.objects.filter(
            type=NotificationType.NotificationTypeChoices.JOB_STATUS
        ).all():
            if (
                notification.user
                not in notification.target.editors_group.user_set.all()
            ):
                if (
                    notification.actor
                    and notification.user == notification.actor
                ):
                    continue
                notification.delete()
                deleted_notification += 1

        print(f"{deleted_notification} notifications deleted.")
