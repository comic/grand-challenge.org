from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now

from tests.factories import UserFactory
from tests.notifications_tests.factories import (
    Forum,
    ForumFactory,
    PostFactory,
    Topic,
    TopicFactory,
)


@pytest.mark.django_db
def test_permission_denied_when_posting(settings):
    settings.FORUMS_MIN_ACCOUNT_AGE_DAYS = 1

    f = ForumFactory(type=Forum.FORUM_POST)
    old_user = UserFactory()
    old_user.date_joined = now() - timedelta(days=2)
    old_user.save()
    topic = TopicFactory(forum=f, poster=old_user, type=Topic.TOPIC_ANNOUNCE)

    user = UserFactory()

    with pytest.raises(PermissionDenied):
        TopicFactory(forum=f, poster=user, type=Topic.TOPIC_ANNOUNCE)

    with pytest.raises(PermissionDenied):
        PostFactory(poster=user, topic=topic)

    user.date_joined = now() - timedelta(days=2)
    user.save()

    TopicFactory(forum=f, poster=user, type=Topic.TOPIC_ANNOUNCE)
    PostFactory(poster=user, topic=topic)
