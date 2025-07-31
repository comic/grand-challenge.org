import logging

from actstream.actions import follow
from django.apps import apps
from django.db import transaction

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.notifications.models import Notification, NotificationType

logger = logging.getLogger(__name__)


@acks_late_micro_short_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def create_forum_notifications(*, object_pk, app_label, model_name):
    from grandchallenge.discussion_forums.models import (
        ForumPost,
        ForumTopic,
        ForumTopicKindChoices,
    )

    model = apps.get_model(app_label=app_label, model_name=model_name)

    if model not in (ForumPost, ForumTopic):
        logger.error(
            f"Forum notifications can only be created for posts or topics, not for {type(object)}"
        )
        return

    obj = model.objects.get(pk=object_pk)

    follow(
        user=obj.creator,
        obj=obj.topic if isinstance(obj, ForumPost) else obj,
        actor_only=False,
        send_action=False,
    )

    if isinstance(obj, ForumPost):
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.FORUM_POST_REPLY,
            actor=obj.creator,
            message="replied to",
            target=obj.topic,
        )
    elif obj.kind == ForumTopicKindChoices.ANNOUNCE:
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.FORUM_POST,
            actor=obj.creator,
            message="announced",
            action_object=obj,
            target=obj.forum,
            context_class="info",
        )
    else:
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.FORUM_POST,
            actor=obj.creator,
            message="posted",
            action_object=obj,
            target=obj.forum,
        )
