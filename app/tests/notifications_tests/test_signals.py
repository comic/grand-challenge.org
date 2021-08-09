import pytest
from actstream.actions import follow, is_following
from actstream.models import Action, Follow
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Topic

from grandchallenge.notifications.models import Notification
from tests.factories import ChallengeFactory, UserFactory
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


@pytest.mark.django_db
def test_follow_clean_up_after_topic_removal():
    u = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t1 = TopicFactory(forum=f, type=Topic.TOPIC_POST)
    t2 = TopicFactory(forum=f, type=Topic.TOPIC_POST)
    follow(u, t1, send_action=False)
    follow(u, t2, send_action=False)

    t1.delete()

    assert not is_following(u, t1)


@pytest.mark.django_db
def test_follow_clean_up_after_post_removal():
    u = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, type=Topic.TOPIC_POST)
    p1 = PostFactory(topic=t, poster=u)
    p2 = PostFactory(topic=t, poster=u)

    follow(u, p1)
    follow(u, p2)

    p1.delete()

    assert not is_following(u, p1)


@pytest.mark.django_db
def test_follow_clean_up_after_forum_removal():
    u = UserFactory()
    f1 = ForumFactory(type=Forum.FORUM_POST)
    f2 = ForumFactory(type=Forum.FORUM_POST)
    follow(u, f1, send_action=False)
    follow(u, f2, send_action=False)

    f1.delete()

    assert not is_following(u, f1)


@pytest.mark.django_db
def test_notification_for_actor_only_when_only_action_object_specified():
    # When an action does not have a target, but an action object instead,
    # only the actor of the action should get notified.
    # Though not intuitive, currently this is necessary to allow sending
    # notifications to new challenge admins without also notifying
    # existing challenge admins.
    # If the challenge were the target or the actor of the action instead,
    # all existing challenge admins would get notified as well.

    user = UserFactory()
    admin = UserFactory()
    # create a challenge with user as admin
    challenge = ChallengeFactory(creator=admin)

    # clear existing notifications for easier testing below
    Notification.objects.all().delete()

    # add user as admin to challenge
    challenge.add_admin(user)
    # under the hood this sends an action with the challenge as action object
    # and the user as actor
    # i.e., action.send(sender=user, verb="added as admin for", action_object=challenge)

    assert Notification.objects.count() == 1
    assert Notification.objects.get().user == user
    assert Notification.objects.get().user != admin
