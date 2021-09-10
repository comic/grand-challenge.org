from actstream.actions import follow
from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.notifications.models import (
    Notification,
    NotificationTypeChoices,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        updated_follows = 0
        deleted_notification_count = 0

        for algorithm in Algorithm.objects.all():
            for admin in algorithm.editors_group.user_set.all():
                try:
                    f = Follow.objects.filter(
                        user=admin,
                        object_id=algorithm.pk,
                        content_type=ContentType.objects.filter(
                            model="algorithm"
                        ).get(),
                        flag="",
                    ).get()
                    f.flag = "access_request"
                    f.save()
                    updated_follows += 1
                except Follow.DoesNotExist:
                    follow(
                        user=admin,
                        obj=algorithm,
                        actor_only=False,
                        send_action=False,
                        flag="access_request",
                    )

        # delete wrong notifications
        for notification in Notification.objects.filter(
            type=NotificationTypeChoices.ACCESS_REQUEST,
            target_content_type=ContentType.objects.filter(
                model="algorithm"
            ).get(),
        ).all():
            if not notification.target.is_editor(notification.user):
                notification.delete()
                deleted_notification_count += 1

        print(f"{updated_follows} follows updated.")
        print(f"{deleted_notification_count} wrong notifications deleted")
