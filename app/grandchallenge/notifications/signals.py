from actstream import action
from django.db.models.signals import post_save
from django.dispatch import receiver
from machina.apps.forum_conversation.models import Topic


@receiver(post_save, sender=Topic)
def create_topic_action(sender, *, instance, created, **__):
    if created and int(instance.type) == int(Topic.TOPIC_ANNOUNCE):
        action.send(
            sender=instance.poster,
            verb="announced",
            action_object=instance,
            target=instance.forum,
            context_class="info",
        )
