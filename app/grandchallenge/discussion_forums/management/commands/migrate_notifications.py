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

        _, deleted_count = Notification.objects.filter(
            Q(target_content_type__in=[old_forum_ct, old_forumtopic_ct])
            | Q(
                action_object_content_type__in=[
                    old_forum_ct,
                    old_forumtopic_ct,
                ]
            )
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {deleted_count} notifications"
            )
        )
