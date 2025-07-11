from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from machina.apps.forum.models import Forum as MachinaForum
from machina.apps.forum_conversation.models import Topic as MachinaTopic

from grandchallenge.discussion_forums.models import (
    Forum,
    ForumTopic,
    get_matching_forum,
    get_matching_topic,
)


class Command(BaseCommand):
    help = "Migrates follows"

    def handle(self, *args, **options):

        new_topic_ct = ContentType.objects.get_for_model(ForumTopic)
        new_forum_ct = ContentType.objects.get_for_model(Forum)
        old_forum_ct = ContentType.objects.get_for_model(MachinaForum)
        old_forumtopic_ct = ContentType.objects.get_for_model(MachinaTopic)

        follows_to_update = []
        n_updated = 0
        batch_size = 1000

        for follow in (
            Follow.objects.filter(
                content_type__in=[old_forum_ct, old_forumtopic_ct]
            )
            .only("object_id", "content_type")
            .iterator(chunk_size=batch_size)
        ):
            if follow.content_type == old_forum_ct:
                try:
                    forum = get_matching_forum(
                        old_forum_id=follow.object_id,
                        old_forum_model=MachinaForum,
                    )
                except ObjectDoesNotExist:
                    continue
                follow.object_id = forum.pk
                follow.content_type = new_forum_ct
            else:
                try:
                    topic = get_matching_topic(
                        old_topic_id=follow.object_id,
                        old_topic_model=MachinaTopic,
                        new_topic_model=ForumTopic,
                    )
                except ObjectDoesNotExist:
                    continue
                follow.object_id = topic.pk
                follow.content_type = new_topic_ct

            follows_to_update.append(follow)

            if len(follows_to_update) >= batch_size:
                Follow.objects.bulk_update(
                    follows_to_update,
                    fields=["content_type", "object_id"],
                )
                n_batch = len(follows_to_update)
                n_updated += n_batch
                self.stdout.write(
                    self.style.HTTP_INFO(
                        f"Updated batch of {n_batch} follows. "
                        f"Total updated so far: {n_updated}"
                    )
                )
                follows_to_update = []

        if follows_to_update:
            Follow.objects.bulk_update(
                follows_to_update,
                fields=["content_type", "object_id"],
            )
            n_updated += len(follows_to_update)

        self.stdout.write(
            self.style.SUCCESS(f"Updated a total of {n_updated} follows.")
        )
