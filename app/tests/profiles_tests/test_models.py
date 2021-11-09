import pytest
from actstream.actions import follow
from guardian.shortcuts import assign_perm

from grandchallenge.notifications.models import Notification
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_notification_preference_created():
    u = UserFactory()

    prefs = u.user_profile

    assert prefs
    assert prefs.user == u
    assert prefs.receive_notification_emails is True
    assert prefs.notification_email_last_sent_at is None
    assert prefs.has_unread_notifications is False


@pytest.mark.django_db
def test_notifications_filtered():
    u1 = UserFactory()
    u2 = UserFactory()

    follow(u1, u2)

    n = NotificationFactory(
        user=u1, type=Notification.Type.GENERIC, actor=u1, message="says hi"
    )

    assert u2.user_profile.has_unread_notifications is False
    assert u1.user_profile.has_unread_notifications is True

    n.read = True
    n.save()

    assert u1.user_profile.has_unread_notifications is False


@pytest.mark.django_db
def test_submit_email_preference(client):
    u1 = UserFactory()
    u2 = UserFactory()

    assert u1.user_profile.receive_newsletter is None
    assert u2.user_profile.receive_newsletter is None

    # give the user right to view and change their own profile information
    assign_perm("change_userprofile", u1, u1.user_profile)
    assign_perm("view_userprofile", u1, u1.user_profile)
    # DRF also requires the global permission
    assign_perm("profiles.change_userprofile", u1)

    response = get_view_for_user(
        viewname="api:profiles-user-detail",
        client=client,
        method=client.patch,
        data={"receive_newsletter": True},
        reverse_kwargs={"pk": u1.pk},
        content_type="application/json",
        user=u1,
    )
    assert response.status_code == 200
    u1.user_profile.refresh_from_db()
    u1.user_profile.refresh_from_db()
    assert u1.user_profile.receive_newsletter

    response = get_view_for_user(
        viewname="api:profiles-user-detail",
        client=client,
        method=client.patch,
        data={"receive_newsletter": True},
        reverse_kwargs={"pk": u1.pk},
        content_type="application/json",
        user=u2,
    )
    assert response.status_code == 404
