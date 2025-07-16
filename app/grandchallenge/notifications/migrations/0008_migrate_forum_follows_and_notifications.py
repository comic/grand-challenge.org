from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations
from django.db.models import Q

from grandchallenge.discussion_forums.models import (
    get_matching_forum,
    get_matching_topic,
)


def migrate_forum_and_topic_follows_and_notifications(  # noqa C901
    apps, schema_editor
):
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
    old_forum_ct = ContentType.objects.get_for_model(MachinaForum)
    old_forumtopic_ct = ContentType.objects.get_for_model(MachinaTopic)

    # delete old notifications with outdated references
    _, deleted_count = Notification.objects.filter(
        Q(target_content_type__in=[old_forum_ct, old_forumtopic_ct])
        | Q(
            action_object_content_type__in=[
                old_forum_ct,
                old_forumtopic_ct,
            ]
        )
    ).delete()
    print(f"Successfully deleted {deleted_count} notifications.")

    follows_to_update = []
    n_updated = 0
    batch_size = 1000

    existing_follows = set(
        Follow.objects.filter(
            content_type__in=[new_forum_ct, new_topic_ct]
        ).values_list("content_type__pk", "object_id", "user__pk")
    )

    for follow in (
        Follow.objects.filter(
            content_type__in=[old_forum_ct, old_forumtopic_ct]
        )
        .only("object_id", "content_type")
        .iterator(chunk_size=batch_size)
    ):
        if follow.content_type == old_forum_ct:
            try:
                forum = get_matching_forum(
                    old_forum_id=follow.object_id,
                    old_forum_model=MachinaForum,
                    new_forum_model=Forum,
                )
            except ObjectDoesNotExist:
                continue
            follow.object_id = forum.pk
            follow.content_type = new_forum_ct
        else:
            try:
                topic = get_matching_topic(
                    old_topic_id=follow.object_id,
                    old_topic_model=MachinaTopic,
                    new_topic_model=ForumTopic,
                )
            except ObjectDoesNotExist:
                continue
            follow.object_id = topic.pk
            follow.content_type = new_topic_ct

        key = (follow.content_type.pk, str(follow.object_id), follow.user.pk)
        if key not in existing_follows:
            follows_to_update.append(follow)
            existing_follows.add(key)

        if len(follows_to_update) >= batch_size:
            Follow.objects.bulk_update(
                follows_to_update,
                fields=["content_type", "object_id"],
            )
            n_batch = len(follows_to_update)
            n_updated += n_batch
            print(
                f"Updated batch of {n_batch} follows. "
                f"Total updated so far: {n_updated}"
            )
            follows_to_update = []

    if follows_to_update:
        Follow.objects.bulk_update(
            follows_to_update,
            fields=["content_type", "object_id"],
        )
        n_updated += len(follows_to_update)

    print(f"Updated a total of {n_updated} follows.")


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
