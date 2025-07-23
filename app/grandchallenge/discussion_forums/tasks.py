import logging

from actstream.actions import follow
from django.apps import apps

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.notifications.models import Notification, NotificationType

logger = logging.getLogger(__name__)


@acks_late_micro_short_task()
def create_forum_notifications(*, object_pk, app_label, model_name):
    from grandchallenge.discussion_forums.models import (
        ForumPost,
        ForumTopic,
        ForumTopicKindChoices,
    )

    model = apps.get_model(app_label=app_label, model_name=model_name)
    object = model.objects.get(pk=object_pk)

    if not isinstance(object, (ForumPost, ForumTopic)):
        logger.error(
            f"Forum notifications can only be created for posts or topics, not for {type(object)}"
        )
        return

    follow(
        user=object.creator,
        obj=object.topic if isinstance(object, ForumPost) else object,
        actor_only=False,
        send_action=False,
    )

    if isinstance(object, ForumPost):
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.FORUM_POST_REPLY,
            actor=object.creator,
            message="replied to",
            target=object.topic,
        )
    elif (
        isinstance(object, ForumTopic)
        and object.kind == ForumTopicKindChoices.ANNOUNCE
    ):
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.FORUM_POST,
            actor=object.creator,
            message="announced",
            action_object=object,
            target=object.forum,
            context_class="info",
        )
    else:
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.FORUM_POST,
            actor=object.creator,
            message="posted",
            action_object=object,
            target=object.forum,
        )
