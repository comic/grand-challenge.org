import pytest
from actstream.actions import follow, is_following
from actstream.models import Follow
from django.conf import settings
from django.urls import reverse
from machina.apps.forum.models import Forum

from grandchallenge.notifications.models import Notification
from tests.factories import (
    ChallengeFactory,
    UserFactory,
)
from tests.notifications_tests.factories import (
    ForumFactory,
    PostFactory,
    Topic,
    TopicFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_logged_in_view(client):
    viewname = "notifications:list"
    response = get_view_for_user(client=client, viewname=viewname, user=None)
    assert response.status_code == 302
    assert response.url == f"{settings.LOGIN_URL}?next={reverse(viewname)}"


@pytest.mark.django_db
def test_last_read_updated(client):
    viewname = "notifications:list"
    u = UserFactory()

    last_read_time = u.user_profile.notifications_last_read_at
    assert last_read_time is not None

    response = get_view_for_user(client=client, viewname=viewname, user=u)
    assert response.status_code == 200

    u.user_profile.refresh_from_db()
    assert u.user_profile.notifications_last_read_at > last_read_time


@pytest.mark.django_db
def test_notification_mark_as_read_or_unread(client):
    user1 = UserFactory()
    user2 = UserFactory()
    c = ChallengeFactory(creator=user1)
    c.add_participant(user=user2)
    _ = TopicFactory(forum=c.forum, poster=user1, type=Topic.TOPIC_POST)

    notification = Notification.objects.get()
    assert not notification.read

    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.post,
        data={"checkbox": notification.id, "mark_read": True},
        user=user2,
    )
    assert response.status_code == 302
    assert Notification.objects.get().read

    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.post,
        data={"checkbox": notification.id, "mark_unread": True},
        user=user2,
    )
    assert response.status_code == 302
    assert not Notification.objects.get().read


@pytest.mark.django_db
def test_notification_deletion(client):
    user1 = UserFactory()
    user2 = UserFactory()
    c = ChallengeFactory(creator=user1)
    c.add_participant(user=user2)
    _ = TopicFactory(forum=c.forum, poster=user1, type=Topic.TOPIC_POST)

    assert len(Notification.objects.all()) == 1
    notification = Notification.objects.get()

    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.post,
        data={"checkbox": notification.id, "delete": True},
        user=user2,
    )
    assert response.status_code == 302
    assert len(Notification.objects.all()) == 0


@pytest.mark.django_db
def test_notification_permission(client):
    user1 = UserFactory()
    user2 = UserFactory()
    c = ChallengeFactory(creator=user1)
    c.add_participant(user=user2)
    _ = TopicFactory(forum=c.forum, poster=user1, type=Topic.TOPIC_POST)

    notification = Notification.objects.get()
    assert notification.user == user2
    assert len(Notification.objects.all()) == 1

    # user can only see notifications they are owners off and have permission to change
    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.get,
        user=user2,
    )
    assert response.status_code == 200
    assert str(notification.action.action_object) in response.rendered_content

    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.get,
        user=user1,
    )
    assert response.status_code == 200
    assert (
        str(notification.action.action_object) not in response.rendered_content
    )
    assert "You have no notifications" in response.rendered_content

    # users can only delete notifications if they are the owner of the notification
    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.post,
        data={"checkbox": notification.id, "delete": True},
        user=user1,
    )
    assert response.status_code == 403
    # notification has not been deleted, because user1 is not the owner of the notification

    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.post,
        data={"checkbox": notification.id, "delete": True},
        user=user2,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_subscribe_to_forum(client):
    user1 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)

    assert not is_following(user1, f)
    breakpoint()
    response = get_view_for_user(
        viewname="notifications:follow-create",
        client=client,
        method=client.post,
        data={"user": user1.id, "forum": f.id},
        user=user1,
    )
    assert response.status_code == 302
    assert is_following(user1, f)
    # check that user gets a notification when a topic is posted in forum
    user2 = UserFactory()
    _ = TopicFactory(forum=f, poster=user2, type=Topic.TOPIC_POST)
    assert len(Notification.objects.filter(user=user1)) == 1


@pytest.mark.django_db
def test_subscribe_to_topic(client):
    user1 = UserFactory()
    user2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, poster=user2, type=Topic.TOPIC_POST)

    assert not is_following(user1, t)

    response = get_view_for_user(
        viewname="notifications:subscription-create",
        client=client,
        method=client.post,
        data={"user": user1.id, "topic": t.id},
        user=user1,
    )
    assert response.status_code == 302
    assert is_following(user1, t)


@pytest.mark.django_db
def test_subscription_delete_permission(client):
    user1 = UserFactory()
    user2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, poster=user1, type=Topic.TOPIC_POST)
    assert is_following(user1, t)

    response = get_view_for_user(
        viewname="notifications:subscription-delete",
        client=client,
        method=client.post,
        data={
            "user": user1.id,
            "subscription_object": Follow.objects.get().id,
        },
        reverse_kwargs={"pk": Follow.objects.get().id},
        user=user2,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="notifications:subscription-delete",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "subscription_object": Follow.objects.get().id,
        },
        reverse_kwargs={"pk": Follow.objects.get().id},
        user=user1,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_unsubscribe_from_topic(client):
    user1 = UserFactory()
    user2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t1 = TopicFactory(forum=f, poster=user2, type=Topic.TOPIC_POST)
    t2 = TopicFactory(forum=f, poster=user2, type=Topic.TOPIC_POST)

    assert is_following(user=user2, obj=t1)
    assert is_following(user=user2, obj=t2)

    _ = PostFactory(topic=t1, poster=user1)
    # check that a notification was created after a reply was posted in subscribed topic
    assert len(Notification.objects.filter(user=user2)) == 1
    Notification.objects.all().delete()

    # unsubscribe from topic t1
    response = get_view_for_user(
        viewname="notifications:subscription-delete",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "subscription_object": Follow.objects.filter(user=user2)
            .first()
            .id,
        },
        reverse_kwargs={"pk": Follow.objects.filter(user=user2).first().id},
        user=user2,
    )
    assert response.status_code == 302
    assert not is_following(user=user2, obj=t1)
    assert is_following(user=user2, obj=t2)
    # check that user no longer gets a notification when a reply is posted in topic
    _ = PostFactory(topic=t1, poster=user1)
    assert len(Notification.objects.filter(user=user2)) == 0


@pytest.mark.django_db
def test_unsubscribe_from_forum(client):
    user1 = UserFactory()
    user2 = UserFactory()
    f1 = ForumFactory(type=Forum.FORUM_POST)
    f2 = ForumFactory(type=Forum.FORUM_POST)
    follow(user2, f1)
    follow(user2, f2)

    _ = TopicFactory(forum=f1, poster=user1, type=Topic.TOPIC_POST)
    # check that notification is created when someone posts a topic in the forum
    assert len(Notification.objects.filter(user=user2)) == 1
    Notification.objects.all().delete()

    # unsubscribe from topic f1
    response = get_view_for_user(
        viewname="notifications:subscription-delete",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "subscription_object": Follow.objects.filter(user=user2)
            .first()
            .id,
        },
        reverse_kwargs={"pk": Follow.objects.filter(user=user2).first().id},
        user=user2,
    )
    assert response.status_code == 302
    assert not is_following(user=user2, obj=f1)
    assert is_following(user=user2, obj=f2)
    # check that user no longer receives a notification when someone posts a topic in the forum
    _ = TopicFactory(forum=f1, poster=user1, type=Topic.TOPIC_POST)
    assert len(Notification.objects.filter(user=user2)) == 0
