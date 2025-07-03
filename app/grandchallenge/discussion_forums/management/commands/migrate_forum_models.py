from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
)


class Command(BaseCommand):
    help = "Migrates forums, topics and posts"

    def handle(self, *args, **options):  # noqa C901
        topic_type_matching_dict = {
            0: ForumTopicKindChoices.DEFAULT,
            1: ForumTopicKindChoices.STICKY,
            2: ForumTopicKindChoices.ANNOUNCE,
        }

        topic_lock_matching_dict = {0: False, 1: True}

        for challenge in Challenge.objects.all():
            self.stdout.write(
                self.style.HTTP_INFO(f"Processing forum for {challenge}")
            )
            try:
                new_forum = challenge.forum.migrated_forum
            except ObjectDoesNotExist:
                new_forum = Forum.objects.create(
                    source_object=challenge.forum,
                    created=challenge.forum.created,
                    modified=challenge.forum.updated,
                )

            challenge.discussion_forum = new_forum
            # calling save also assigns forum permissions (in the migration we need to do this manually)
            challenge.save()

            topic_count = 0
            post_count = 0

            for topic in challenge.forum.topics.all():
                try:
                    new_topic = topic.migrated_topic
                except ObjectDoesNotExist:
                    new_topic = ForumTopic.objects.create(
                        source_object=topic,
                        forum=new_forum,
                        creator=topic.poster,
                        subject=topic.subject,
                        kind=topic_type_matching_dict[topic.type],
                        last_post_on=topic.last_post_on,
                        created=topic.created,
                        modified=topic.updated,
                        is_locked=topic_lock_matching_dict[topic.status],
                    )
                    topic_count += 1

                latest_new_post = None
                for post in topic.posts.filter(
                    migrated_post__isnull=True
                ).all():
                    # posts are ordered by creation time, so the last post we create here
                    # will correspond to the latest post and can be saved as that on the
                    # topic
                    try:
                        latest_new_post = post.migrated_post
                    except ObjectDoesNotExist:
                        latest_new_post = ForumPost.objects.create(
                            source_object=post,
                            topic=new_topic,
                            created=post.created,
                            modified=post.updated,
                            creator=post.poster,
                            content=post.content,
                        )
                        post_count += 1

                if latest_new_post:
                    new_topic.last_post = latest_new_post
                    new_topic.save()

            self.stdout.write(
                self.style.SUCCESS(
                    "Finished migrating forum, topics and posts for {}. Migrated {} topics and {} posts".format(
                        challenge, topic_count, post_count
                    )
                )
            )
