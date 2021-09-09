from actstream.actions import follow
from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from guardian.shortcuts import assign_perm
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Post, Topic

from grandchallenge.notifications.models import Notification, NotificationType


@receiver(post_save, sender=Topic)
def create_topic_notification(sender, *, instance, created, **_):
    if created:
        follow(
            user=instance.poster,
            obj=instance,
            actor_only=False,
            send_action=False,
        )

        if int(instance.type) == int(Topic.TOPIC_ANNOUNCE):
            Notification.send(
                type=NotificationType.NotificationTypeChoices.FORUM_POST,
                actor=instance.poster,
                message="announced",
                action_object=instance,
                target=instance.forum,
                context_class="info",
            )
        else:
            Notification.send(
                type=NotificationType.NotificationTypeChoices.FORUM_POST,
                actor=instance.poster,
                message="posted",
                action_object=instance,
                target=instance.forum,
            )


@receiver(post_save, sender=Post)
def create_post_notification(sender, *, instance, created, **_):
    if (
        created
        and instance.topic.posts_count != 0
        and not instance.is_topic_head
    ):
        follow(
            user=instance.poster,
            obj=instance.topic,
            actor_only=False,
            send_action=False,
        )
        Notification.send(
            type=NotificationType.NotificationTypeChoices.FORUM_POST_REPLY,
            actor=instance.poster,
            message="replied to",
            target=instance.topic,
        )


@receiver(post_save, sender=Follow)
def add_permissions(*, instance, created, **_):
    if created:
        assign_perm("change_follow", instance.user, instance)
        assign_perm("delete_follow", instance.user, instance)
        assign_perm("view_follow", instance.user, instance)


@receiver(pre_delete, sender=Topic)
@receiver(pre_delete, sender=Forum)
@receiver(pre_delete, sender=Post)
def clean_up_follows(*, instance, **_):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(content_type=ct, object_id=instance.pk).delete()
