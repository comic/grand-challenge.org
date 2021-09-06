import pytest
from actstream.actions import follow
from actstream.models import Follow
from django.conf import settings
from django.db import connection, reset_queries
from machina.apps.forum.models import Forum

from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.utils import (
    prefetch_generic_foreign_key_objects,
)
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory
from tests.notifications_tests.factories import (
    ForumFactory,
    NotificationFactory,
)


@pytest.mark.django_db
def test_notification_list_view_num_queries(client, django_assert_num_queries):
    user1 = UserFactory()
    _ = NotificationFactory(
        user=user1,
        message="requested access to",
        target=AlgorithmFactory(),
        type=Notification.Type.ACCESS_REQUEST,
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
    # double check that there is an action target for the test below to be meaningful
    assert notifications[0].target

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
    finally:
        settings.DEBUG = False
        reset_queries()


@pytest.mark.django_db
def test_follow_list_view_num_queries():
    user1 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
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
