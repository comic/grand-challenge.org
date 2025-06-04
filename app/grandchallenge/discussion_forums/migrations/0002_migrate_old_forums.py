from django.db import migrations

from grandchallenge.discussion_forums.models import ForumTopicKindChoices


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
        new_forum = Forum.objects.create()
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
                is_locked=topic_lock_matching_dict[topic.status],
            )

            for post in topic.posts.all():
                ForumPost.objects.create(
                    topic=new_topic,
                    created=post.created,
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

    def get_matching_forum(*, old_forum_id):
        old_forum = MachinaForum.objects.get(pk=old_forum_id)
        return old_forum.challenge.discussion_forum

    def get_matching_topic(*, old_topic_id):
        old_topic = MachinaTopic.objects.get(pk=old_topic_id)
        new_forum = get_matching_forum(old_forum_id=old_topic.forum.pk)
        return ForumTopic.objects.get(
            forum=new_forum,
            creator=old_topic.poster,
            subject=old_topic.subject,
        )

    for track in TopicReadTrack.objects.iterator(chunk_size=1000):
        new_topic = get_matching_topic(old_topic_id=track.topic.pk)
        TopicReadRecord.objects.create(topic=new_topic, user=track.user)


class Migration(migrations.Migration):
    dependencies = [
        ("discussion_forums", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_challenge_forums, elidable=True),
        migrations.RunPython(migrate_topic_tracks, elidable=True),
    ]
