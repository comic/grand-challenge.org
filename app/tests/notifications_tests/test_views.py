import pytest
from actstream.actions import is_following, unfollow
from actstream.models import Follow
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from grandchallenge.notifications.models import Notification
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.discussion_forums_tests.factories import (
    ForumFactory,
    ForumTopicFactory,
)
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_logged_in_view(client):
    viewname = "notifications:list"
    response = get_view_for_user(client=client, viewname=viewname, user=None)
    assert response.status_code == 302
    assert response.url == f"{settings.LOGIN_URL}?next={reverse(viewname)}"


@pytest.mark.django_db
def test_notification_mark_as_read_or_unread(client):
    user = UserFactory()
    notification = NotificationFactory(
        user=user, type=Notification.Type.GENERIC
    )

    assert not notification.read

    response = get_view_for_user(
        viewname="api:notification-detail",
        client=client,
        method=client.patch,
        data={"read": True},
        reverse_kwargs={"pk": notification.id},
        content_type="application/json",
        user=user,
    )

    assert response.status_code == 200
    assert Notification.objects.get().read

    response = get_view_for_user(
        viewname="api:notification-detail",
        client=client,
        method=client.patch,
        data={"read": False},
        reverse_kwargs={"pk": notification.id},
        content_type="application/json",
        user=user,
    )

    assert response.status_code == 200
    assert not Notification.objects.get().read


@pytest.mark.django_db
def test_notification_deletion(client):
    user = UserFactory()
    notification = NotificationFactory(
        user=user, type=Notification.Type.GENERIC
    )

    response = get_view_for_user(
        viewname="api:notification-detail",
        client=client,
        method=client.delete,
        reverse_kwargs={"pk": notification.id},
        content_type="application/json",
        user=user,
    )

    assert response.status_code == 204
    assert len(Notification.objects.all()) == 0


@pytest.mark.django_db
def test_notification_view_permissions(client):
    user1 = UserFactory()
    user2 = UserFactory()
    notification = NotificationFactory(
        user=user1,
        actor=UserFactory(),
        message="requested access to",
        target=AlgorithmFactory(),
        type=Notification.Type.ACCESS_REQUEST,
    )

    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.get,
        user=user1,
    )
    assert response.status_code == 200
    assert notification in response.context["notification_list"]

    # user2 cannot see user1 notifications
    response = get_view_for_user(
        viewname="notifications:list",
        client=client,
        method=client.get,
        user=user2,
    )
    assert response.status_code == 200

    assert notification not in response.context["notification_list"]
    assert "You have no notifications" in response.rendered_content


@pytest.mark.parametrize(
    "type, data",
    [("delete", {}), ("patch", {"read": True}), ("patch", {"read": False})],
)
@pytest.mark.django_db
def test_notification_update_and_delete_permissions(client, type, data):
    user1 = UserFactory()
    user2 = UserFactory()
    notification = NotificationFactory(
        user=user1, type=Notification.Type.GENERIC
    )

    if type == "delete":
        method = client.delete
    elif type == "patch":
        method = client.patch

    response = get_view_for_user(
        viewname="api:notification-detail",
        client=client,
        method=method,
        data=data,
        reverse_kwargs={"pk": notification.id},
        content_type="application/json",
        user=user2,
    )
    assert response.status_code == 404

    response = get_view_for_user(
        viewname="api:notification-detail",
        client=client,
        method=method,
        data=data,
        reverse_kwargs={"pk": notification.id},
        content_type="application/json",
        user=user1,
    )
    if type == "delete":
        assert response.status_code == 204
    elif type == "patch":
        assert response.status_code == 200


@pytest.mark.django_db
def test_forum_subscribe_and_unsubscribe(client):
    admin = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_admin(admin)

    assert is_following(admin, f)

    response = get_view_for_user(
        viewname="notifications:follow-delete",
        client=client,
        method=client.post,
        user=admin,
        reverse_kwargs={
            "pk": Follow.objects.filter(user=admin, object_id=f.pk).first().id
        },
    )
    assert response.status_code == 302
    assert not is_following(admin, f)

    response = get_view_for_user(
        viewname="notifications:follow-create",
        client=client,
        method=client.post,
        data={
            "user": admin.id,
            "content_type": ContentType.objects.get(
                app_label=f._meta.app_label, model=f._meta.model_name
            ).id,
            "object_id": f.id,
            "actor_only": False,
        },
        user=admin,
    )
    assert response.status_code == 302
    assert is_following(admin, f)


@pytest.mark.django_db
def test_topic_subscribe_and_unsubscribe(client):
    admin = UserFactory()
    user = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_admin(admin)
    f.linked_challenge.add_participant(user)

    t = ForumTopicFactory(forum=f, creator=admin)

    assert is_following(admin, t)
    assert not is_following(user, t)

    response = get_view_for_user(
        viewname="notifications:follow-create",
        client=client,
        method=client.post,
        data={
            "user": user.id,
            "content_type": ContentType.objects.get(
                app_label=t._meta.app_label, model=t._meta.model_name
            ).id,
            "object_id": t.id,
            "actor_only": False,
        },
        user=user,
    )
    assert response.status_code == 302
    assert is_following(user, t)

    response = get_view_for_user(
        viewname="notifications:follow-delete",
        client=client,
        method=client.post,
        reverse_kwargs={
            "pk": Follow.objects.filter(user=user, object_id=t.pk).get().id
        },
        user=user,
    )
    assert response.status_code == 302
    assert not is_following(user, t)


@pytest.mark.django_db
def test_follow_delete_permission(client):
    participant1 = UserFactory()
    participant2 = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(participant1)
    f.linked_challenge.add_participant(participant2)

    assert is_following(participant1, f)

    # users cannot delete someone elses subscription
    response = get_view_for_user(
        viewname="notifications:follow-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"pk": Follow.objects.get(user=participant1).id},
        user=participant2,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="notifications:follow-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"pk": Follow.objects.get(user=participant1).id},
        user=participant1,
    )
    assert response.status_code == 302
    assert not is_following(participant1, f)


@pytest.mark.django_db
def test_follow_create_permission(client):
    user = UserFactory()
    admin = UserFactory()
    participant = UserFactory()
    f = ForumFactory()

    f.linked_challenge.add_admin(admin)
    f.linked_challenge.add_participant(participant)

    # admin and participant automatically follow forum
    assert is_following(admin, f)
    assert is_following(participant, f)
    old_num_follows = Follow.objects.count()

    # not a participant, so cannot subscribe
    response = get_view_for_user(
        viewname="notifications:follow-create",
        client=client,
        method=client.post,
        data={
            "user": user.id,
            "content_type": ContentType.objects.get(
                app_label=f._meta.app_label, model=f._meta.model_name
            ).id,
            "object_id": f.id,
            "actor_only": False,
        },
        user=user,
    )
    assert "You cannot create this subscription" in str(response.content)
    assert len(Follow.objects.all()) == old_num_follows

    # Remove follows
    unfollow(admin, f)
    unfollow(participant, f)

    for u in [admin, participant]:
        response = get_view_for_user(
            viewname="notifications:follow-create",
            client=client,
            method=client.post,
            data={
                "user": u.id,
                "content_type": ContentType.objects.get(
                    app_label=f._meta.app_label, model=f._meta.model_name
                ).id,
                "object_id": f.id,
                "actor_only": False,
            },
            user=u,
        )
        assert response.status_code == 302
        assert is_following(u, f)


@pytest.mark.django_db
def test_follow_deletion_through_api(client):
    participant = UserFactory()
    user = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(participant)

    num_follows = Follow.objects.count()

    # users can only delete their own follows
    response = get_view_for_user(
        viewname="api:follow-detail",
        client=client,
        method=client.delete,
        reverse_kwargs={"pk": Follow.objects.get(user=participant).pk},
        content_type="application/json",
        user=user,
    )
    assert response.status_code == 404

    response = get_view_for_user(
        viewname="api:follow-detail",
        client=client,
        method=client.delete,
        reverse_kwargs={"pk": Follow.objects.get(user=participant).pk},
        content_type="application/json",
        user=participant,
    )
    assert response.status_code == 204
    assert len(Follow.objects.all()) == num_follows - 1


@pytest.mark.django_db
def test_follow_view_permissions(client):
    challenge_participant = UserFactory()
    user = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(challenge_participant)

    assert is_following(challenge_participant, f)

    # user is not subscribed to anything, empty follow list
    response = get_view_for_user(
        viewname="notifications:follow-list",
        client=client,
        method=client.get,
        user=user,
    )
    assert response.status_code == 200
    assert response.context["object_list"].count() == 0

    # challenge participant has 1 subscription to challenge forum
    response = get_view_for_user(
        viewname="notifications:follow-list",
        client=client,
        method=client.get,
        user=challenge_participant,
    )
    assert response.status_code == 200
    assert response.context["object_list"].count() == 1
    assert (
        str(
            Follow.objects.get(
                user=challenge_participant, object_id=f.pk
            ).follow_object
        )
        in response.rendered_content
    )
