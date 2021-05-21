import pytest
from actstream.actions import follow, is_following
from actstream.models import Follow
from django.conf import settings
from django.urls import reverse
from machina.apps.forum.models import Forum

from grandchallenge.notifications.forms import (
    NotificationForm,
    SubscriptionForm,
)
from grandchallenge.notifications.models import Notification
from tests.factories import ChallengeFactory, UserFactory
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
        viewname="notifications:update",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "notification": notification.id,
            "action": NotificationForm.MARK_READ,
        },
        reverse_kwargs={"pk": notification.id},
        user=user2,
    )
    assert response.status_code == 302
    assert Notification.objects.get().read

    response = get_view_for_user(
        viewname="notifications:update",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "notification": notification.id,
            "action": NotificationForm.MARK_UNREAD,
        },
        reverse_kwargs={"pk": notification.id},
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
        viewname="notifications:update",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "notification": notification.id,
            "action": NotificationForm.REMOVE,
        },
        reverse_kwargs={"pk": notification.id},
        user=user2,
    )
    assert response.status_code == 302
    assert len(Notification.objects.all()) == 0


@pytest.mark.django_db
def test_unfollow_topic(client):
    user1 = UserFactory()
    user2 = UserFactory()
    c = ChallengeFactory(creator=user1)
    c.add_participant(user=user2)
    t1 = TopicFactory(forum=c.forum, poster=user1, type=Topic.TOPIC_POST)
    t2 = TopicFactory(forum=c.forum, poster=user1, type=Topic.TOPIC_POST)
    _ = PostFactory(topic=t1, poster=user2)
    _ = PostFactory(topic=t2, poster=user2)

    assert is_following(user=user2, obj=t1)
    assert is_following(user=user2, obj=t2)
    assert len(Notification.objects.filter(user=user2)) == 2
    notification = Notification.objects.filter(user=user2).first()

    # unsubscribe from topic t1
    response = get_view_for_user(
        viewname="notifications:update",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "notification": notification.id,
            "action": NotificationForm.UNFOLLOW,
        },
        reverse_kwargs={"pk": notification.id},
        user=user2,
    )
    assert response.status_code == 302
    assert not is_following(user=user2, obj=t1)
    assert is_following(user=user2, obj=t2)

    assert len(Notification.objects.filter(user=user2)) == 1
    assert str(t1) not in str(
        Notification.objects.filter(user=user2).get().action
    )
    assert str(t2) in str(Notification.objects.filter(user=user2).get().action)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action",
    (
        NotificationForm.MARK_READ,
        NotificationForm.MARK_UNREAD,
        NotificationForm.REMOVE,
        NotificationForm.UNFOLLOW,
    ),
)
def test_notification_update_permissions(client, action):
    user1 = UserFactory()
    user2 = UserFactory()
    c = ChallengeFactory(creator=user1)
    c.add_participant(user=user2)
    _ = TopicFactory(forum=c.forum, poster=user1, type=Topic.TOPIC_POST)

    notification = Notification.objects.get()

    response = get_view_for_user(
        viewname="notifications:update",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "notification": notification.id,
            "action": action,
        },
        reverse_kwargs={"pk": notification.id},
        user=user1,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="notifications:update",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "notification": notification.id,
            "action": action,
        },
        reverse_kwargs={"pk": notification.id},
        user=user2,
    )
    assert response.status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action",
    (
        SubscriptionForm.UNFOLLOW_TOPIC,
        SubscriptionForm.UNFOLLOW_FORUM,
        SubscriptionForm.UNFOLLOW_USER,
    ),
)
def test_subscription_update_permissions(client, action):
    user1 = UserFactory()
    user2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)

    if action == SubscriptionForm.UNFOLLOW_TOPIC:
        t = TopicFactory(forum=f, poster=user1, type=Topic.TOPIC_POST)
        assert is_following(user1, t)
    elif action == SubscriptionForm.UNFOLLOW_FORUM:
        follow(user1, f)
        assert is_following(user1, f)
    elif action == SubscriptionForm.UNFOLLOW_USER:
        follow(user1, user2)
        assert is_following(user1, user2)

    response = get_view_for_user(
        viewname="notifications:subscription-update",
        client=client,
        method=client.post,
        data={
            "user": user1.id,
            "subscription_object": Follow.objects.get().id,
            "action": action,
        },
        reverse_kwargs={"pk": Follow.objects.get().id},
        user=user2,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="notifications:subscription-update",
        client=client,
        method=client.post,
        data={
            "user": user2.id,
            "subscription_object": Follow.objects.get().id,
            "action": action,
        },
        reverse_kwargs={"pk": Follow.objects.get().id},
        user=user1,
    )
    assert response.status_code == 302
