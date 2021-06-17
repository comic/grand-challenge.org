import pytest
from actstream.actions import follow
from actstream.models import Action, Follow
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Topic

from grandchallenge.notifications.models import Notification
from tests.factories import UserFactory
from tests.notifications_tests.factories import (
    ForumFactory,
    PostFactory,
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
def test_notification_created_for_target_followers_on_action_creation():
    user1 = UserFactory()
    user2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    follow(user1, f, send_action=False)
    follow(user2, f, send_action=False)

    # creating a post creates an action automatically
    _ = TopicFactory(forum=f, poster=user1, type=Topic.TOPIC_POST)
    assert len(Action.objects.all()) == 1

    assert len(Notification.objects.all()) == 1
    notification = Notification.objects.get()
    # check that the poster did not receive a notification
    assert notification.user == user2
    assert notification.user != user1
