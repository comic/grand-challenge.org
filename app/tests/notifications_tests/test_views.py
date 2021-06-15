import pytest
from actstream.actions import is_following
from actstream.models import Follow
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from machina.apps.forum.models import Forum

from grandchallenge.notifications.models import Notification
from tests.factories import (
    ChallengeFactory,
    UserFactory,
)
from tests.notifications_tests.factories import (
    ForumFactory,
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
def test_notification_permissions(client):
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
    assert response.status_code == 404

    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.post,
        data={"checkbox": notification.id, "delete": True},
        user=user2,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_forum_subscribe_and_unsubscribe(client):
    user1 = UserFactory()
    c = ChallengeFactory(creator=user1)

    assert is_following(user1, c.forum)

    response = get_view_for_user(
        viewname="notifications:follow-delete",
        client=client,
        method=client.post,
        user=user1,
        reverse_kwargs={"pk": Follow.objects.filter(user=user1).first().id},
    )
    assert response.status_code == 302
    assert not is_following(user1, c.forum)

    response = get_view_for_user(
        viewname="notifications:follow-create",
        client=client,
        method=client.post,
        data={
            "user": user1.id,
            "content_type": ContentType.objects.get(
                app_label=c.forum._meta.app_label,
                model=c.forum._meta.model_name,
            ).id,
            "object_id": c.forum.id,
            "actor_only": False,
        },
        user=user1,
    )
    assert response.status_code == 302
    assert is_following(user1, c.forum)


@pytest.mark.django_db
def test_topic_subscribe_and_unsubscribe(client):
    user1 = UserFactory()
    user2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, poster=user2, type=Topic.TOPIC_POST)

    assert not is_following(user1, t)

    response = get_view_for_user(
        viewname="notifications:follow-create",
        client=client,
        method=client.post,
        data={
            "user": user1.id,
            "content_type": ContentType.objects.get(
                app_label=t._meta.app_label, model=t._meta.model_name,
            ).id,
            "object_id": t.id,
            "actor_only": False,
        },
        user=user1,
    )
    assert response.status_code == 302
    assert is_following(user1, t)

    response = get_view_for_user(
        viewname="notifications:follow-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"pk": Follow.objects.filter(user=user1).first().id},
        user=user1,
    )
    assert response.status_code == 302
    assert not is_following(user1, t)


@pytest.mark.django_db
def test_subscription_delete_permission(client):
    user1 = UserFactory()
    user2 = UserFactory()
    f = ForumFactory(type=Forum.FORUM_POST)
    t = TopicFactory(forum=f, poster=user1, type=Topic.TOPIC_POST)
    assert is_following(user1, t)

    response = get_view_for_user(
        viewname="notifications:follow-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"pk": Follow.objects.get().id},
        user=user2,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="notifications:follow-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"pk": Follow.objects.get().id},
        user=user1,
    )
    assert response.status_code == 302
