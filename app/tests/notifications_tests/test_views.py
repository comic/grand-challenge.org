import pytest
from django.conf import settings
from django.urls import reverse

from grandchallenge.notifications.forms import NotificationForm
from grandchallenge.notifications.models import Notification
from tests.factories import ChallengeFactory, UserFactory
from tests.notifications_tests.factories import (
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
            "notification": notification.id,
            "action": NotificationForm.REMOVE,
        },
        reverse_kwargs={"pk": notification.id},
        user=user2,
    )
    assert response.status_code == 302
    assert len(Notification.objects.all()) == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action",
    (
        NotificationForm.MARK_READ,
        NotificationForm.MARK_UNREAD,
        NotificationForm.REMOVE,
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
        data={"notification": notification.id, "action": action},
        reverse_kwargs={"pk": notification.id},
        user=user1,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="notifications:update",
        client=client,
        method=client.post,
        data={"notification": notification.id, "action": action},
        reverse_kwargs={"pk": notification.id},
        user=user2,
    )
    assert response.status_code == 302
