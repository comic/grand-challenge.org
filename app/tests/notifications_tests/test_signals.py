import pytest
from actstream.models import Action

from tests.factories import UserFactory
from tests.notifications_tests.factories import (
    Forum,
    ForumFactory,
    Topic,
    TopicFactory,
)


@pytest.mark.django_db
def test_action_created_on_new_topic():
    u = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, poster=u, type=Topic.TOPIC_ANNOUNCE)

    action = Action.objects.get()
    assert str(action).startswith(f"{u} created {t} on {f}")
