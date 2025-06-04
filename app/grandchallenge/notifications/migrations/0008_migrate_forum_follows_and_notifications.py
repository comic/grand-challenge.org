from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations

from grandchallenge.notifications.models import NotificationTypeChoices


def migrate_forum_and_topic_follows_and_notifications(apps, schema_editor):
    Notification = apps.get_model(  # noqa: N806
        "notifications", "Notification"
    )
    Follow = apps.get_model("actstream", "Follow")  # noqa: N806
    Forum = apps.get_model("discussion_forums", "Forum")  # noqa: N806
    ForumTopic = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumTopic"
    )
    MachinaForum = apps.get_model("forum", "Forum")  # noqa: N806
    MachinaTopic = apps.get_model("forum_conversation", "Topic")  # noqa: N806
    ContentType = apps.get_model("contenttypes", "ContentType")  # noqa: N806

    new_topic_ct = ContentType.objects.get_for_model(ForumTopic)
    new_forum_ct = ContentType.objects.get_for_model(Forum)

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

    # delete old notifications with outdated references
    Notification.objects.filter(
        type__in=[
            NotificationTypeChoices.FORUM_POST,
            NotificationTypeChoices.FORUM_POST_REPLY,
        ]
    ).delete()

    ct_forum = ContentType.objects.get_for_model(MachinaForum)
    ct_forumtopic = ContentType.objects.get_for_model(MachinaTopic)

    follows_to_update = []
    batch_size = 1000
    for follow in (
        Follow.objects.filter(content_type__in=[ct_forum, ct_forumtopic])
        .only("object_id", "content_type")
        .iterator(chunk_size=batch_size)
    ):
        if follow.content_type == ct_forum:
            try:
                forum = get_matching_forum(old_forum_id=follow.object_id)
            except ObjectDoesNotExist:
                continue
            follow.object_id = forum.pk
            follow.content_type = new_forum_ct
        else:
            topic = get_matching_topic(old_topic_id=follow.object_id)
            follow.object_id = topic.pk
            follow.content_type = new_topic_ct

        follows_to_update.append(follow)

        if follows_to_update >= batch_size:
            Follow.objects.bulk_update(
                follows_to_update,
                fields=["content_type", "object_id"],
            )
            follows_to_update = []

    if follows_to_update:
        Follow.objects.bulk_update(
            follows_to_update,
            fields=["content_type", "object_id"],
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "notifications",
            "0007_followgroupobjectpermission_notificatio_group_i_cc45cf_idx_and_more",
        ),
        ("discussion_forums", "0002_migrate_old_forums"),
    ]

    operations = [
        migrations.RunPython(
            migrate_forum_and_topic_follows_and_notifications, elidable=True
        ),
    ]
