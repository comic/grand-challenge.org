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
            notification.save()
        elif notification.type == NotificationTypeChoices.FORUM_POST_REPLY:
            new_target = get_matching_topic(
                old_topic_id=notification.target_object_id
            )
            notification.target = new_target
            notification.save()
        else:
            # nothing to do
            continue

    ct_forum = ContentType.objects.filter(
        app_label="forum", model="forum"
    ).get()
    ct_forumtopic = ContentType.objects.filter(
        app_label="forum_conversation", model="topic"
    ).get()

    for follow in Follow.objects.filter(
        content_type__in=[ct_forum, ct_forumtopic]
    ):
        if follow.content_type == ct_forum:
            forum = get_matching_forum(old_forum_id=follow.object_id)
            follow.content_type = ContentType.objects.get_for_model(Forum)
            follow.follow_object = forum
            follow.object_id = forum.pk
            follow.save()
        elif follow.content_type == ct_forumtopic:
            topic = get_matching_topic(old_topic_id=follow.object_id)
            follow.content_type = ContentType.objects.get_for_model(ForumTopic)
            follow.follow_object = topic
            follow.object_id = topic.pk
            follow.save()


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
