from django.db import migrations

from grandchallenge.discussion_forums.models import TopicTypeChoices


def migrate_challenge_forums(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")  # noqa: N806
    Forum = apps.get_model("discussion_forums", "Forum")  # noqa: N806
    Topic = apps.get_model("discussion_forums", "Topic")  # noqa: N806
    Post = apps.get_model("discussion_forums", "Post")  # noqa: N806

    topic_type_matching_dict = {
        0: TopicTypeChoices.DEFAULT,
        1: TopicTypeChoices.STICKY,
        2: TopicTypeChoices.ANNOUNCE,
    }

    for challenge in Challenge.objects.all():
        old_forum = challenge.forum
        new_forum = Forum.objects.create(name=old_forum.name)
        challenge.discussion_forum = new_forum
        challenge.save()

        for topic in old_forum.topics.all():
            new_topic = Topic.objects.create(
                forum=new_forum,
                creator=topic.poster,
                subject=topic.subject,
                type=topic_type_matching_dict[topic.type],
                last_post_on=topic.last_post_on,
            )

            for post in topic.posts.all():
                Post.objects.create(
                    topic=new_topic,
                    creator=post.poster,
                    subject=post.subject,
                    content=post.content,
                )


class Migration(migrations.Migration):
    dependencies = [
        ("discussion_forums", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_challenge_forums, elidable=True),
    ]
