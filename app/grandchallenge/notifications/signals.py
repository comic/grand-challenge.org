from actstream import action
from django.db.models.signals import post_save
from django.dispatch import receiver
from machina.apps.forum_conversation.models import Topic


@receiver(post_save, sender=Topic)
def create_topic_action(_, *, instance, created, **__):
    if created:
        action.send(
            sender=instance.poster,
            verb="created",
            action_object=instance,
            target=instance.forum,
        )
