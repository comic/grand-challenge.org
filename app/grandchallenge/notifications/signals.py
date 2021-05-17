from actstream import action
from actstream.actions import follow
from actstream.models import Action, followers
from django.db.models.signals import post_save
from django.dispatch import receiver
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

        for follower in followers(instance.forum):
            # only send notifications to followers other than the poster
            if follower is not instance.poster:
                Notification(
                    user=follower, action=Action.objects.first()
                ).save()


@receiver(post_save, sender=Post)
def create_post_action(sender, *, instance, created, **_):
    if created and not instance.is_topic_head:
        follow(
            user=instance.poster,
            obj=instance.topic,
            actor_only=False,
            send_action=False,
        )

        action.send(
            sender=instance.poster, verb="replied to", target=instance.topic,
        )

        for follower in followers(instance.topic):
            # only send notifications to followers other than the poster
            if follower != instance.poster:
                Notification(
                    user=follower, action=Action.objects.first()
                ).save()
