from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations

from grandchallenge.discussion_forums.models import (
    ForumTopicKindChoices,
    get_matching_topic,
)


def migrate_challenge_forums(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")  # noqa: N806
    Forum = apps.get_model("discussion_forums", "Forum")  # noqa: N806
    ForumTopic = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumTopic"
    )
    ForumPost = apps.get_model("discussion_forums", "ForumPost")  # noqa: N806

    topic_type_matching_dict = {
        0: ForumTopicKindChoices.DEFAULT,
        1: ForumTopicKindChoices.STICKY,
        2: ForumTopicKindChoices.ANNOUNCE,
    }

    topic_lock_matching_dict = {0: False, 1: True}

    for challenge in Challenge.objects.all():
        new_forum = Forum.objects.create(
            created=challenge.forum.created, modified=challenge.forum.updated
        )
        challenge.discussion_forum = new_forum
        challenge.save()

        for topic in challenge.forum.topics.all():
            new_topic = ForumTopic.objects.create(
                forum=new_forum,
                creator=topic.poster,
                subject=topic.subject,
                kind=topic_type_matching_dict[topic.type],
                last_post_on=topic.last_post_on,
                created=topic.created,
                modified=topic.updated,
                is_locked=topic_lock_matching_dict[topic.status],
            )

            for post in topic.posts.all():
                ForumPost.objects.create(
                    topic=new_topic,
                    created=post.created,
                    modified=post.updated,
                    creator=post.poster,
                    content=post.content,
                )


def migrate_topic_tracks(apps, schema_editor):
    TopicReadTrack = apps.get_model(  # noqa: N806
        "forum_tracking", "TopicReadTrack"
    )
    TopicReadRecord = apps.get_model(  # noqa: N806
        "discussion_forums", "TopicReadRecord"
    )
    MachinaForum = apps.get_model("forum", "Forum")  # noqa: N806
    MachinaTopic = apps.get_model("forum_conversation", "Topic")  # noqa: N806
    ForumTopic = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumTopic"
    )

    batch_size = 1000
    batch = []
    total_created = 0
    num_tracks_to_create = TopicReadTrack.objects.count()

    for track in TopicReadTrack.objects.iterator(chunk_size=1000):
        try:
            new_topic = get_matching_topic(
                old_topic_id=track.topic.pk,
                old_topic_model=MachinaTopic,
                new_topic_model=ForumTopic,
                old_forum_model=MachinaForum,
            )
        except ObjectDoesNotExist:
            continue
        batch.append(
            TopicReadRecord(
                topic=new_topic,
                user=track.user,
                created=track.mark_time,  # the original model does not have a creation time stamp
                modified=track.mark_time,
            )
        )

        if len(batch) >= batch_size:
            TopicReadRecord.objects.bulk_create(batch)
            total_created += len(batch)
            print(
                f"Created {total_created} new records out of {num_tracks_to_create}"
            )
            batch = []

    if batch:
        TopicReadRecord.objects.bulk_create(batch)
        total_created += len(batch)
        print(
            f"Finished creating TopicReadRecords. Created a total of {total_created} new records."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("discussion_forums", "0001_initial"),
        ("forum_tracking", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_challenge_forums, elidable=True),
        migrations.RunPython(migrate_topic_tracks, elidable=True),
    ]
