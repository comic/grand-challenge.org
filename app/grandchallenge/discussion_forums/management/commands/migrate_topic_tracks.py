from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from machina.apps.forum.models import Forum as MachinaForum
from machina.apps.forum_conversation.models import Topic as MachinaTopic
from machina.apps.forum_tracking.models import TopicReadTrack

from grandchallenge.discussion_forums.models import (
    ForumTopic,
    TopicReadRecord,
    get_matching_topic,
)


class Command(BaseCommand):
    help = "Migrates topic read records"

    def handle(self, *args, **options):
        batch_size = 1000
        batch = []
        total_created = 0
        num_tracks_to_create = (
            TopicReadTrack.objects.filter(migrated_track__isnull=True)
            .exclude(user__username=settings.ANONYMOUS_USER_NAME)
            .count()
        )

        if num_tracks_to_create == 0:
            self.stdout.write(
                self.style.SUCCESS("No TopicReadTracks to migrate")
            )
            return

        for track in (
            TopicReadTrack.objects.filter(migrated_track__isnull=True)
            .exclude(user__username=settings.ANONYMOUS_USER_NAME)
            .iterator(chunk_size=1000)
        ):
            try:
                new_topic = get_matching_topic(
                    old_topic_id=track.topic.pk,
                    old_topic_model=MachinaTopic,
                    new_topic_model=ForumTopic,
                    old_forum_model=MachinaForum,
                )
            except ObjectDoesNotExist:
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
                    self.style.SUCCESS(
                        "Created {} new records out of {}".format(
                            total_created, num_tracks_to_create
                        )
                    )
                )
                batch = []

        if batch:
            TopicReadRecord.objects.bulk_create(batch)
            total_created += len(batch)
            self.stdout.write(
                self.style.SUCCESS(
                    "Finished creating TopicReadRecords. Created a total of {} new records".format(
                        total_created
                    )
                )
            )
