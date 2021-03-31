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
@pytest.mark.parametrize(
    "kind,should_create",
    (
        (Topic.TOPIC_ANNOUNCE, True),
        (Topic.TOPIC_POST, False),
        (Topic.TOPIC_STICKY, False),
    ),
)
def test_action_created_on_new_topic(kind, should_create):
    p = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, poster=p, type=kind)

    if should_create:
        action = Action.objects.get()
        assert str(action).startswith(f"{p} announced {t} on {f}")
    else:
        assert Action.objects.exists() is False
