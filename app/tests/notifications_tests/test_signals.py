import pytest
from actstream.actions import follow, is_following
from actstream.models import Follow
from django.utils.html import format_html
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Topic

from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.templatetags.profiles import user_profile_link
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
def test_notification_sent_on_new_topic(kind):
    p = UserFactory()
    u = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    follow(user=u, obj=f)
    t = TopicFactory(forum=f, poster=p, type=kind)

    notification = Notification.objects.get()
    topic_string = format_html('<a href="{}">{}</a>', t.get_absolute_url(), t)
    if kind == Topic.TOPIC_ANNOUNCE:
        assert notification.print_notification(user=u).startswith(
            f"{user_profile_link(p)} announced {topic_string}"
        )
    else:
        assert notification.print_notification(user=u).startswith(
            f"{user_profile_link(p)} posted {topic_string}"
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind", (Topic.TOPIC_ANNOUNCE, Topic.TOPIC_POST, Topic.TOPIC_STICKY,),
)
def test_notification_sent_on_new_post(kind):
    u1 = UserFactory()
    u2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    follow(user=u2, obj=f)
    t = TopicFactory(forum=f, poster=u1, type=kind)
    PostFactory(topic=t, poster=u2)

    notifications = Notification.objects.all()
    topic_string = format_html('<a href="{}">{}</a>', t.get_absolute_url(), t)
    forum_string = format_html('<a href="{}">{}</a>', f.get_absolute_url(), f)
    assert len(notifications) == 2
    assert (
        notifications[1]
        .print_notification(user=u1)
        .startswith(f"{user_profile_link(u2)} replied to {topic_string}")
    )

    if kind == Topic.TOPIC_ANNOUNCE:
        assert (
            notifications[0]
            .print_notification(user=u2)
            .startswith(
                f"{user_profile_link(t.poster)} announced {topic_string} in {forum_string}"
            )
        )
    else:
        assert (
            notifications[0]
            .print_notification(user=u2)
            .startswith(
                f"{user_profile_link(t.poster)} posted {topic_string} in {forum_string}"
            )
        )


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
def test_notification_for_new_admin_only():
    user = UserFactory()
    admin = UserFactory()
    challenge = ChallengeFactory(creator=admin)

    # clear existing notifications for easier testing below
    Notification.objects.all().delete()

    # add user as admin to challenge
    challenge.add_admin(user)

    assert Notification.objects.count() == 1
    assert Notification.objects.get().user == user
    assert Notification.objects.get().user != admin
