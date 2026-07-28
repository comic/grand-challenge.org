from uuid import UUID

from actstream.actions import follow
from django.apps import apps
from django.db import transaction
from lambda_tasks.decorators import lambda_task
from lambda_tasks.logging import task_logger

from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.utils.query import check_lock_acquired
from grandchallenge.notifications.models import (
    Notification,
    NotificationTypeChoices,
)


@lambda_task(retry_on=(LockNotAcquiredException,))
def create_forum_notifications(
    *, object_pk: str | UUID, app_label: str, model_name: str
):
    from grandchallenge.discussion_forums.models import (
        ForumPost,
        ForumTopic,
        ForumTopicKindChoices,
    )

    model = apps.get_model(app_label=app_label, model_name=model_name)

    if model not in (ForumPost, ForumTopic):
        task_logger.error(
            f"Forum notifications can only be created for posts or topics, not for {model}"
        )
        return

    try:
        # Do not lock here as notifications (and emails) might take a while to be created,
        # rather, we apply a lock at the end of this task.
        obj = model.objects.get(pk=object_pk)
    except model.DoesNotExist:
        task_logger.error(
            "Forum notifications are not created because the object no longer exists."
        )
        return  # Nothing to do here

    follow(
        user=obj.creator,
        obj=obj.topic if isinstance(obj, ForumPost) else obj,
        actor_only=False,
        send_action=False,
    )

    if isinstance(obj, ForumPost):
        Notification.send(
            kind=NotificationTypeChoices.FORUM_POST_REPLY,
            actor=obj.creator,
            message="replied to",
            target=obj.topic,
        )
    elif obj.kind == ForumTopicKindChoices.ANNOUNCE:
        Notification.send(
            kind=NotificationTypeChoices.FORUM_POST,
            actor=obj.creator,
            message="announced",
            action_object=obj,
            target=obj.forum,
            context_class="info",
        )
    else:
        Notification.send(
            kind=NotificationTypeChoices.FORUM_POST,
            actor=obj.creator,
            message="posted",
            action_object=obj,
            target=obj.forum,
        )

    # To prevent orphaned notifications we do a final check on the existence
    # of the action object and lock it for the remainder of the transaction.
    with check_lock_acquired():  # Will be retried if the lock is not acquired
        try:
            model.objects.select_for_update(nowait=True).get(pk=object_pk)
        except (
            model.DoesNotExist
        ):  # Silently rollback without raising an exception
            task_logger.error(
                "Forum notifications are not created because the object no longer exists."
            )
            transaction.set_rollback(True)
