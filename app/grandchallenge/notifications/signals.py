from actstream import action
from actstream.actions import follow, is_following
from actstream.models import Action, Follow, followers
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from guardian.shortcuts import assign_perm
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Post, Topic

from grandchallenge.notifications.models import Notification


@receiver(post_save, sender=Topic)
def create_topic_action(sender, *, instance, created, **_):
    if created:
        follow(
            user=instance.poster,
            obj=instance,
            actor_only=False,
            send_action=False,
        )

        if int(instance.type) == int(Topic.TOPIC_ANNOUNCE):
            action.send(
                sender=instance.poster,
                verb="announced",
                action_object=instance,
                target=instance.forum,
                context_class="info",
            )
        else:
            action.send(
                sender=instance.poster,
                verb="posted",
                action_object=instance,
                target=instance.forum,
            )


@receiver(post_save, sender=Post)
def create_post_action(sender, *, instance, created, **_):
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

        action.send(
            sender=instance.poster, verb="replied to", target=instance.topic,
        )


@receiver(post_save, sender=Action)
def create_notification(*, instance, **_):
    if instance.target:
        if instance.target_content_type.model == "phase":
            follower_group = [
                admin
                for admin in instance.target.challenge.get_admins()
                if is_following(admin, instance.target)
            ]
            if instance.actor_content_type.model == "evaluation":
                follower_group.append(instance.actor.submission.creator)
        else:
            follower_group = followers(instance.target)
        for follower in follower_group:
            # only send notifications to followers other than the poster
            if follower != instance.actor:
                Notification(user=follower, action=instance).save()
    elif instance.action_object:
        # notify only the actor when there is not target, but an action object
        Notification(user=instance.actor, action=instance).save()
    else:
        follower_group = followers(instance.actor)
        for follower in follower_group:
            # only send notifications to followers other than the poster
            if follower != instance.actor:
                Notification(user=follower, action=instance).save()


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
