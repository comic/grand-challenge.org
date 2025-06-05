import pytest
from actstream.actions import follow
from actstream.models import Follow
from django.conf import settings
from django.db import connection, reset_queries

from grandchallenge.evaluation.models import Evaluation
from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.utils import (
    prefetch_generic_foreign_key_objects,
)
from tests.discussion_forums_tests.factories import ForumFactory
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory


@pytest.mark.django_db
def test_notification_list_view_num_queries(client, django_assert_num_queries):
    user1 = UserFactory()
    phase = PhaseFactory()
    eval = EvaluationFactory(
        submission__phase=phase,
        status=Evaluation.FAILURE,
        time_limit=phase.evaluation_time_limit,
    )

    # delete all prior notifications for easier testing below
    Notification.objects.all().delete()

    # create notification
    _ = NotificationFactory(
        user=user1,
        type=Notification.Type.EVALUATION_STATUS,
        actor=eval.submission.creator,
        message="failed",
        action_object=eval,
        target=phase,
    )

    notifications = Notification.objects.select_related(
        "actor_content_type",
        "target_content_type",
        "action_object_content_type",
        "user",
    ).all()

    notifications_with_prefetched_fks = prefetch_generic_foreign_key_objects(
        Notification.objects.select_related(
            "actor_content_type",
            "target_content_type",
            "action_object_content_type",
            "user",
        ).all()
    )

    try:
        settings.DEBUG = True
        notifications[0].target
        # when the generic foreign keys have not been prefetched, accessing the
        # action target, result in two db calls
        assert len(connection.queries) == 2
        reset_queries()
        notifications_with_prefetched_fks[0].target
        # when gfks have been prefetched, accessing the action target
        # no longer requires any db calls
        assert len(connection.queries) == 0
        # related objects of the generic foreign keys have also been prefetched
        notifications[0].action_object.submission.phase.challenge
        assert len(connection.queries) == 5
        reset_queries()
        notifications_with_prefetched_fks[
            0
        ].action_object.submission.phase.challenge
        assert len(connection.queries) == 0
    finally:
        settings.DEBUG = False
        reset_queries()


@pytest.mark.django_db
def test_follow_list_view_num_queries():
    user1 = UserFactory()
    f = ForumFactory()
    follow(user=user1, obj=f)

    follows = Follow.objects.select_related("user", "content_type").all()
    follows_with_prefetched_gfks = prefetch_generic_foreign_key_objects(
        Follow.objects.select_related("user", "content_type").all()
    )

    try:
        settings.DEBUG = True
        follows[0].follow_object
        assert len(connection.queries) == 2
        reset_queries()
        follows_with_prefetched_gfks[0].follow_object
        assert len(connection.queries) == 0
    finally:
        settings.DEBUG = False
        reset_queries()
