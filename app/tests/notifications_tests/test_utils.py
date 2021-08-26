import pytest
from actstream.actions import follow
from actstream.models import Follow
from django.conf import settings
from django.db import connection, reset_queries
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Topic

from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.utils import (
    prefetch_generic_foreign_key_objects,
    prefetch_nested_generic_foreign_key_objects,
)
from tests.factories import ChallengeFactory, UserFactory
from tests.notifications_tests.factories import (
    ForumFactory,
    TopicFactory,
)


@pytest.mark.django_db
def test_notification_list_view_num_queries(client, django_assert_num_queries):
    user1 = UserFactory()
    user2 = UserFactory()
    c = ChallengeFactory(creator=user1)
    # delete Notification that resulted from adding a new admin the the challenge
    Notification.objects.all().delete()
    _ = TopicFactory(forum=c.forum, poster=user2, type=Topic.TOPIC_POST)

    notifications = Notification.objects.select_related(
        "action__actor_content_type",
        "action__target_content_type",
        "action__action_object_content_type",
        "user",
    ).all()

    notifications_with_prefetched_gfks = prefetch_nested_generic_foreign_key_objects(
        Notification.objects.select_related(
            "action__actor_content_type",
            "action__target_content_type",
            "action__action_object_content_type",
            "user",
        ).all()
    )
    # double check that there is an action target for the test below to be meaningful
    assert notifications[0].action.target

    try:
        settings.DEBUG = True
        notifications[0].action.target
        # when the generic foreign keys have not been prefetched, accessing the
        # action target, result in two db calls
        assert len(connection.queries) == 2
        reset_queries()
        notifications_with_prefetched_gfks[0].action.target
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
