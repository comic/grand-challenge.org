from django.db import migrations

from grandchallenge.notifications.models import NotificationTypeChoices


def migrate_forum_and_topic_follows_and_notifications(apps, schema_editor):
    Notification = apps.get_model(  # noqa: N806
        "notifications", "Notification"
    )
    Follow = apps.get_model("actstream", "Follow")  # noqa: N806
    ForumTopic = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumTopic"
    )
    MachinaForum = apps.get_model("forum", "Forum")  # noqa: N806
    MachinaTopic = apps.get_model("forum_conversation", "Topic")  # noqa: N806
    ContentType = apps.get_model("contenttypes", "ContentType")  # noqa: N806

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

    notifications_to_update = []
    for notification in Notification.objects.filter(
        type__in=[
            NotificationTypeChoices.FORUM_POST,
            NotificationTypeChoices.FORUM_POST_REPLY,
        ]
    ):
        if notification.type == NotificationTypeChoices.FORUM_POST:
            new_target = get_matching_forum(
                old_forum_id=notification.target_object_id
            )
            new_action_object = get_matching_topic(
                old_topic_id=notification.action_object_object_id
            )
            notification.target = new_target
            notification.action_object = new_action_object
        else:
            new_target = get_matching_topic(
                old_topic_id=notification.target_object_id
            )
            notification.target = new_target
        notifications_to_update.append(notification)

    Notification.objects.bulk_update(
        notifications_to_update,
        fields=[
            "target_content_type",
            "target_object_id",
            "action_object_content_type",
            "action_object_object_id",
        ],
        batch_size=1000,
    )

    ct_forum = ContentType.objects.filter(
        app_label="forum", model="forum"
    ).get()
    ct_forumtopic = ContentType.objects.filter(
        app_label="forum_conversation", model="topic"
    ).get()

    follows_to_update = []
    for follow in Follow.objects.filter(
        content_type__in=[ct_forum, ct_forumtopic]
    ):
        if follow.content_type == ct_forum:
            forum = get_matching_forum(old_forum_id=follow.object_id)
            follow.follow_object = forum
        else:
            topic = get_matching_topic(old_topic_id=follow.object_id)
            follow.follow_object = topic
        follows_to_update.append(follow)

    Follow.objects.bulk_update(
        follows_to_update,
        fields=["content_type", "object_id"],
        batch_size=1000,
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
