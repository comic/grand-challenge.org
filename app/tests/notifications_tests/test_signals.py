import pytest
from actstream.models import Action, Follow

from grandchallenge.notifications.models import Notification
from tests.factories import ChallengeFactory, UserFactory
from tests.notifications_tests.factories import (
    Forum,
    ForumFactory,
    PostFactory,
    Topic,
    TopicFactory,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind", (Topic.TOPIC_ANNOUNCE, Topic.TOPIC_POST, Topic.TOPIC_STICKY,),
)
def test_action_created_on_new_topic(kind):
    p = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, poster=p, type=kind)

    assert Follow.objects.is_following(user=p, instance=t)

    action = Action.objects.get()

    if kind == Topic.TOPIC_ANNOUNCE:
        assert str(action).startswith(f"{p} announced {t} on {f}")
    else:
        assert str(action).startswith(f"{p} posted {t} on {f}")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind", (Topic.TOPIC_ANNOUNCE, Topic.TOPIC_POST, Topic.TOPIC_STICKY,),
)
def test_action_created_on_new_post(kind):
    u = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, type=kind)
    PostFactory(topic=t, poster=u)

    actions = Action.objects.all()

    assert len(actions) == 2
    assert str(actions[0]).startswith(f"{u} replied to {t}")

    if kind == Topic.TOPIC_ANNOUNCE:
        assert str(actions[1]).startswith(f"{t.poster} announced {t} on {f}")
    else:
        assert str(actions[1]).startswith(f"{t.poster} posted {t} on {f}")


@pytest.mark.django_db
def test_follow_if_post_in_topic():
    u = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, type=Topic.TOPIC_POST)
    PostFactory(topic=t, poster=u)

    assert Follow.objects.is_following(user=u, instance=t)


@pytest.mark.django_db
def test_notification_created_on_topic_or_post_creation():
    user1 = UserFactory()
    user2 = UserFactory()
    c = ChallengeFactory(creator=user1)
    c.add_participant(user=user2)

    t = TopicFactory(forum=c.forum, poster=user1, type=Topic.TOPIC_ANNOUNCE)

    notification = Notification.objects.all()
    assert len(notification) == 1
    # check that the poster did not receive a notification
    assert notification[0].user == user2
    assert notification[0].user != user1

    _ = PostFactory(topic=t, poster=user2)

    notification = Notification.objects.all()
    assert len(notification) == 2
    assert notification[1].user == user1
    assert notification[1].user != user2
