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


class Migration(migrations.Migration):
    dependencies = [
        ("discussion_forums", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_challenge_forums, elidable=True),
    ]
