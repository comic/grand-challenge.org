import pytest
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
from tests.notifications_tests.factories import ForumFactory, TopicFactory


@pytest.mark.django_db
def test_notification_list_view_num_queries():
    user1 = UserFactory()
    user2 = UserFactory()
    c = ChallengeFactory(creator=user1)
    _ = TopicFactory(forum=c.forum, poster=user2, type=Topic.TOPIC_POST)
    notifications = Notification.objects.all()
    notifications_with_prefetched_gfks = prefetch_nested_generic_foreign_key_objects(
        Notification.objects.all()
    )

    try:
        settings.DEBUG = True
        notifications[0].action.target
        num_queries_without_prefetching = len(connection.queries)
        reset_queries()
        notifications_with_prefetched_gfks[0].action.target
        assert len(connection.queries) < num_queries_without_prefetching
    finally:
        settings.DEBUG = False
        reset_queries()


@pytest.mark.django_db
def test_follow_list_view_num_queries():
    user1 = UserFactory()
    user2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    _ = TopicFactory(forum=f, poster=user1, type=Topic.TOPIC_POST)
    _ = TopicFactory(forum=f, poster=user2, type=Topic.TOPIC_POST)
    follows = Follow.objects.all()
    follows_with_prefetched_gfks = prefetch_generic_foreign_key_objects(
        Follow.objects.all()
    )

    try:
        settings.DEBUG = True
        follows[0].follow_object.forum
        num_queries_without_prefetching = len(connection.queries)
        reset_queries()
        follows_with_prefetched_gfks[0].follow_object.forum
        assert len(connection.queries) < num_queries_without_prefetching
    finally:
        settings.DEBUG = False
        reset_queries()
