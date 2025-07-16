from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db.models import Q
from machina.apps.forum.models import Forum as MachinaForum
from machina.apps.forum_conversation.models import Topic as MachinaTopic

from grandchallenge.notifications.models import Notification


class Command(BaseCommand):
    help = "Deletes old forum notifications"

    def handle(self, *args, **options):
        old_forum_ct = ContentType.objects.get_for_model(MachinaForum)
        old_forumtopic_ct = ContentType.objects.get_for_model(MachinaTopic)

        batch_size = 5000
        batch_ids = []
        total_deleted = 0

        queryset = Notification.objects.filter(
            Q(target_content_type__in=[old_forum_ct, old_forumtopic_ct])
            | Q(
                action_object_content_type__in=[
                    old_forum_ct,
                    old_forumtopic_ct,
                ]
            )
        ).values_list("pk", flat=True)

        for notification_id in queryset.iterator(chunk_size=batch_size):
            batch_ids.append(notification_id)

            if len(batch_ids) >= batch_size:
                _, deleted_count = Notification.objects.filter(
                    id__in=batch_ids
                ).delete()
                total_deleted += deleted_count.get(
                    "notifications.Notification"
                )
                self.stdout.write(
                    f"Deleted batch of {deleted_count} notifications"
                )
                batch_ids = []

        if batch_ids:
            _, deleted_count = Notification.objects.filter(
                id__in=batch_ids
            ).delete()
            total_deleted += deleted_count.get("notifications.Notification")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {total_deleted} notifications total"
            )
        )
