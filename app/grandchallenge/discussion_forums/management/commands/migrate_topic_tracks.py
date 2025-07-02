from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from machina.apps.forum.models import Forum as MachinaForum
from machina.apps.forum_conversation.models import Topic as MachinaTopic
from machina.apps.forum_tracking.models import ForumReadTrack, TopicReadTrack

from grandchallenge.discussion_forums.models import (
    ForumTopic,
    TopicReadRecord,
    get_matching_topic,
)


class Command(BaseCommand):
    help = "Migrates topic read records"

    def handle(self, *args, **options):  # noqa C901
        batch_size = 1000
        batch = []
        total_created = 0

        topic_mapping = {}
        for old_id in MachinaTopic.objects.values_list("pk", flat=True):
            try:
                topic_mapping[old_id] = get_matching_topic(
                    old_topic_id=old_id,
                    old_topic_model=MachinaTopic,
                    new_topic_model=ForumTopic,
                    old_forum_model=MachinaForum,
                )
            except ObjectDoesNotExist:
                continue

        for track in (
            TopicReadTrack.objects.filter(migrated_track__isnull=True)
            .exclude(user__username=settings.ANONYMOUS_USER_NAME)
            .iterator(chunk_size=batch_size)
        ):
            try:
                new_topic = topic_mapping[track.topic.pk]
            except KeyError:
                continue

            if track.user.has_perm("view_forumtopic", new_topic):
                batch.append(
                    TopicReadRecord(
                        source_object=track,
                        topic=new_topic,
                        user=track.user,
                        created=track.mark_time,  # the original model does not have a creation time stamp
                        modified=track.mark_time,
                    )
                )

            if len(batch) >= batch_size:
                TopicReadRecord.objects.bulk_create(batch)
                total_created += len(batch)
                self.stdout.write(
                    self.style.SUCCESS(f"Created {total_created} new records")
                )
                batch = []

        if batch:
            TopicReadRecord.objects.bulk_create(batch)
            total_created += len(batch)
            self.stdout.write(
                self.style.SUCCESS(f"Created {total_created} new records")
            )
            batch = []

        for track in ForumReadTrack.objects.exclude(
            user__username=settings.ANONYMOUS_USER_NAME
        ).iterator(chunk_size=1000):
            for topic in track.forum.topics.filter(
                updated__lte=track.mark_time
            ).all():
                try:
                    new_topic = topic_mapping[topic.pk]
                except KeyError:
                    continue

                existing_topic_ids = set(
                    TopicReadRecord.objects.filter(
                        user=track.user,
                    ).values_list("topic__pk", flat=True)
                )

                if (
                    track.user.has_perm("view_forumtopic", new_topic)
                    and new_topic.pk not in existing_topic_ids
                ):
                    batch.append(
                        TopicReadRecord(
                            topic=new_topic,
                            user=track.user,
                            created=track.mark_time,
                            modified=track.mark_time,
                        )
                    )

                if len(batch) >= batch_size:
                    TopicReadRecord.objects.bulk_create(batch)
                    total_created += len(batch)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created {total_created} new records"
                        )
                    )
                    batch = []

        if batch:
            TopicReadRecord.objects.bulk_create(batch)
            total_created += len(batch)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Finished creating TopicReadRecords. Created a total of {total_created} new records"
                )
            )
