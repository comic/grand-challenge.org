from django.db import migrations

from grandchallenge.discussion_forums.models import TopicKindChoices


def migrate_challenge_forums(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")  # noqa: N806
    Forum = apps.get_model("discussion_forums", "Forum")  # noqa: N806
    Topic = apps.get_model("discussion_forums", "Topic")  # noqa: N806
    Post = apps.get_model("discussion_forums", "Post")  # noqa: N806

    topic_type_matching_dict = {
        0: TopicKindChoices.DEFAULT,
        1: TopicKindChoices.STICKY,
        2: TopicKindChoices.ANNOUNCE,
    }

    for challenge in Challenge.objects.all():
        new_forum = Forum.objects.create()
        challenge.discussion_forum = new_forum
        challenge.save()

        for topic in challenge.forum.topics.all():
            new_topic = Topic.objects.create(
                forum=new_forum,
                creator=topic.poster,
                subject=topic.subject,
                kind=topic_type_matching_dict[topic.type],
                last_post_on=topic.last_post_on,
                created=topic.created,
            )

            for post in topic.posts.all():
                Post.objects.create(
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
