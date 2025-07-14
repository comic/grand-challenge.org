from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations

from grandchallenge.discussion_forums.models import (
    ForumTopicKindChoices,
    get_matching_topic,
)


def init_forum_permissions(*, apps, challenge):
    Permission = apps.get_model("auth", "Permission")  # noqa: N806
    ForumGroupObjectPermission = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumGroupObjectPermission"
    )

    admins_group = challenge.admins_group
    participants_group = challenge.participants_group
    view_permission = Permission.objects.get(
        codename="view_forum",
        content_type__app_label="discussion_forums",
    )
    create_forum_topic_permission = Permission.objects.get(
        codename="create_forum_topic",
        content_type__app_label="discussion_forums",
    )
    create_sticky_and_announcement_topic_permission = Permission.objects.get(
        codename="create_sticky_and_announcement_topic",
        content_type__app_label="discussion_forums",
    )

    if challenge.display_forum_link:
        ForumGroupObjectPermission.objects.create(
            content_object=challenge.discussion_forum,
            group=admins_group,
            permission=view_permission,
        )
        ForumGroupObjectPermission.objects.create(
            content_object=challenge.discussion_forum,
            group=participants_group,
            permission=view_permission,
        )
        ForumGroupObjectPermission.objects.create(
            content_object=challenge.discussion_forum,
            group=admins_group,
            permission=create_forum_topic_permission,
        )
        ForumGroupObjectPermission.objects.create(
            content_object=challenge.discussion_forum,
            group=participants_group,
            permission=create_forum_topic_permission,
        )
        ForumGroupObjectPermission.objects.create(
            content_object=challenge.discussion_forum,
            group=admins_group,
            permission=create_sticky_and_announcement_topic_permission,
        )


def init_topic_permissions(*, apps, topic):
    Permission = apps.get_model("auth", "Permission")  # noqa: N806
    ForumTopicGroupObjectPermission = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumTopicGroupObjectPermission"
    )

    challenge = topic.forum.linked_challenge
    admins_group = challenge.admins_group
    participants_group = challenge.participants_group

    view_permission = Permission.objects.get(
        codename="view_forumtopic",
        content_type__app_label="discussion_forums",
    )
    create_topic_post_permission = Permission.objects.get(
        codename="create_topic_post",
        content_type__app_label="discussion_forums",
    )
    lock_forumtopic_permission = Permission.objects.get(
        codename="lock_forumtopic",
        content_type__app_label="discussion_forums",
    )
    delete_permission = Permission.objects.get(
        codename="delete_forumtopic",
        content_type__app_label="discussion_forums",
    )

    ForumTopicGroupObjectPermission.objects.create(
        content_object=topic,
        group=admins_group,
        permission=view_permission,
    )
    ForumTopicGroupObjectPermission.objects.create(
        content_object=topic,
        group=participants_group,
        permission=view_permission,
    )
    ForumTopicGroupObjectPermission.objects.create(
        content_object=topic,
        group=admins_group,
        permission=create_topic_post_permission,
    )
    ForumTopicGroupObjectPermission.objects.create(
        content_object=topic,
        group=participants_group,
        permission=create_topic_post_permission,
    )
    ForumTopicGroupObjectPermission.objects.create(
        content_object=topic,
        group=admins_group,
        permission=lock_forumtopic_permission,
    )
    ForumTopicGroupObjectPermission.objects.create(
        content_object=topic,
        group=admins_group,
        permission=delete_permission,
    )


def init_post_permissions(*, apps, post):
    Permission = apps.get_model("auth", "Permission")  # noqa: N806
    ForumPostGroupObjectPermission = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumPostGroupObjectPermission"
    )
    ForumPostUserObjectPermission = apps.get_model(  # noqa: N806
        "discussion_forums", "ForumPostUserObjectPermission"
    )

    challenge = post.topic.forum.linked_challenge
    admins_group = challenge.admins_group
    participants_group = challenge.participants_group

    view_permission = Permission.objects.get(
        codename="view_forumpost",
        content_type__app_label="discussion_forums",
    )
    delete_permission = Permission.objects.get(
        codename="delete_forumpost",
        content_type__app_label="discussion_forums",
    )
    change_permission = Permission.objects.get(
        codename="change_forumpost",
        content_type__app_label="discussion_forums",
    )

    ForumPostGroupObjectPermission.objects.create(
        content_object=post,
        group=admins_group,
        permission=view_permission,
    )
    ForumPostGroupObjectPermission.objects.create(
        content_object=post,
        group=participants_group,
        permission=view_permission,
    )
    ForumPostGroupObjectPermission.objects.create(
        content_object=post,
        group=admins_group,
        permission=delete_permission,
    )
    if post.creator:
        ForumPostUserObjectPermission.objects.create(
            content_object=post,
            user=post.creator,
            permission=delete_permission,
        )
        ForumPostUserObjectPermission.objects.create(
            content_object=post,
            user=post.creator,
            permission=change_permission,
        )


def migrate_challenge_forums(apps, schema_editor):  # noqa C901
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
        print(f"Processing forum for {challenge.short_name}")

        try:
            new_forum = challenge.forum.migrated_forum
        except ObjectDoesNotExist:
            new_forum = Forum.objects.create(
                source_object=challenge.forum,
                created=challenge.forum.created,
                modified=challenge.forum.updated,
            )
            challenge.discussion_forum = new_forum
            challenge.save()
            init_forum_permissions(apps=apps, challenge=challenge)

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
                init_topic_permissions(apps=apps, topic=new_topic)
                topic_count += 1

            latest_new_post = None
            for post in topic.posts.filter(migrated_post__isnull=True).all():
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
                    init_post_permissions(apps=apps, post=latest_new_post)
                    post_count += 1

            if latest_new_post:
                new_topic.last_post = latest_new_post
                new_topic.save()

        print(
            f"Finished migrating forum, topics and posts for {challenge.short_name}. Migrated {topic_count} topics and {post_count} posts"
        )


def migrate_topic_tracks(apps, schema_editor):  # noqa: C901
    TopicReadTrack = apps.get_model(  # noqa: N806
        "forum_tracking", "TopicReadTrack"
    )
    ForumReadTrack = apps.get_model(  # noqa: N806
        "forum_tracking", "ForumReadTrack"
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

    topic_mapping = {}
    for old_id in MachinaTopic.objects.values_list("pk", flat=True):
        try:
            topic_mapping[old_id] = get_matching_topic(
                old_topic_id=old_id,
                old_topic_model=MachinaTopic,
                new_topic_model=ForumTopic,
                old_forum_model=MachinaForum,
            )
        except ObjectDoesNotExist:
            continue

    for track in (
        TopicReadTrack.objects.filter(migrated_track__isnull=True)
        .exclude(user__username=settings.ANONYMOUS_USER_NAME)
        .iterator(chunk_size=1000)
    ):
        try:
            new_topic = topic_mapping[track.topic.pk]
        except KeyError:
            continue

        admins_group = new_topic.forum.linked_challenge.admins_group
        participants_group = (
            new_topic.forum.linked_challenge.participants_group
        )
        if track.user.groups.filter(
            pk__in=[admins_group.pk, participants_group.pk]
        ).exists():
            batch.append(
                TopicReadRecord(
                    source_object=track,
                    topic=new_topic,
                    user=track.user,
                    created=track.mark_time,  # the original model does not have a creation time stamp
                    modified=track.mark_time,
                )
            )

        if len(batch) >= batch_size:
            TopicReadRecord.objects.bulk_create(batch)
            total_created += len(batch)
            print(f"Created {total_created} new records")
            batch = []

    if batch:
        TopicReadRecord.objects.bulk_create(batch)
        total_created += len(batch)
        print(f"Created {total_created} new records.")
        batch = []

    for track in ForumReadTrack.objects.exclude(
        user__username=settings.ANONYMOUS_USER_NAME
    ).iterator(chunk_size=1000):
        for topic in track.forum.topics.filter(
            updated__lte=track.mark_time
        ).all():
            try:
                new_topic = topic_mapping[topic.pk]
            except KeyError:
                continue

            existing_topic_ids = set(
                TopicReadRecord.objects.filter(
                    user=track.user,
                ).values_list("topic__pk", flat=True)
            )

            if new_topic.pk in existing_topic_ids:
                continue
            else:
                admins_group = new_topic.forum.linked_challenge.admins_group
                participants_group = (
                    new_topic.forum.linked_challenge.participants_group
                )
                if track.user.groups.filter(
                    pk__in=[admins_group.pk, participants_group.pk]
                ).exists():
                    batch.append(
                        TopicReadRecord(
                            topic=new_topic,
                            user=track.user,
                            created=track.mark_time,
                            modified=track.mark_time,
                        )
                    )

            if len(batch) >= batch_size:
                TopicReadRecord.objects.bulk_create(batch)
                total_created += len(batch)
                print(f"Created {total_created} new records")
                batch = []

    if batch:
        TopicReadRecord.objects.bulk_create(batch)
        total_created += len(batch)

    print(
        f"Finished creating TopicReadRecords. "
        f"Created a total of {total_created} new records"
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
