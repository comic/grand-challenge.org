from contextlib import nullcontext

import pytest
from actstream.actions import follow
from django.contrib.sites.models import Site
from django.core import mail

from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.models import (
    EmailSubscriptionTypes,
    NotificationEmailOptions,
)
from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_notification_preference_created():
    u = UserFactory()

    prefs = u.user_profile

    assert prefs
    assert prefs.user == u
    assert (
        prefs.notification_email_choice
        is NotificationEmailOptions.DAILY_SUMMARY
    )
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
def test_submit_newsletter_preference(client):
    u1 = UserFactory()
    u2 = UserFactory()

    assert u1.user_profile.receive_newsletter is None
    assert u2.user_profile.receive_newsletter is None

    response = get_view_for_user(
        viewname="newsletter-sign-up",
        client=client,
        method=client.post,
        data={"receive_newsletter": True},
        reverse_kwargs={"username": u1.username},
        user=u1,
    )
    assert response.status_code == 302
    u1.user_profile.refresh_from_db()
    assert u1.user_profile.receive_newsletter

    response = get_view_for_user(
        viewname="newsletter-sign-up",
        client=client,
        method=client.post,
        data={"receive_newsletter": True},
        reverse_kwargs={"username": u1.username},
        user=u2,
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_dispatch_notifications_email():
    user = UserFactory()
    site = Site.objects.get()
    assert not user.user_profile.notification_email_last_sent_at

    user.user_profile.dispatch_unread_notifications_email(
        site=site, unread_notification_count=1
    )
    assert user.user_profile.notification_email_last_sent_at
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


@pytest.mark.parametrize(
    "subscription_type,subscription_attr,subscription_preference,expectation",
    (
        (
            EmailSubscriptionTypes.NOTIFICATION,
            "notification_email_choice",
            NotificationEmailOptions.DAILY_SUMMARY,
            nullcontext(),
        ),
        (
            EmailSubscriptionTypes.NOTIFICATION,
            "notification_email_choice",
            NotificationEmailOptions.INSTANT,
            nullcontext(),
        ),
        (
            EmailSubscriptionTypes.NOTIFICATION,
            "notification_email_choice",
            NotificationEmailOptions.DISABLED,
            pytest.raises(ValueError),
        ),
        (
            EmailSubscriptionTypes.NEWSLETTER,
            "receive_newsletter",
            True,
            nullcontext(),
        ),
        (
            EmailSubscriptionTypes.NEWSLETTER,
            "receive_newsletter",
            False,
            pytest.raises(ValueError),
        ),
        (EmailSubscriptionTypes.SYSTEM, None, None, nullcontext()),
    ),
)
@pytest.mark.django_db
def test_get_unsubscribe_link_only_when_subscribed(
    subscription_type,
    subscription_attr,
    subscription_preference,
    expectation,
):
    user = UserFactory()
    if subscription_preference:
        setattr(user.user_profile, subscription_attr, subscription_preference)
    with expectation:
        user.user_profile.get_unsubscribe_link(
            subscription_type=subscription_type
        )


@pytest.mark.parametrize(
    "subscription_type,subscription_attr,subscription_preference,unsubscribe_viewname",
    (
        (
            EmailSubscriptionTypes.NOTIFICATION,
            "notification_email_choice",
            NotificationEmailOptions.DAILY_SUMMARY,
            "notification-unsubscribe",
        ),
        (
            EmailSubscriptionTypes.NOTIFICATION,
            "notification_email_choice",
            NotificationEmailOptions.INSTANT,
            "notification-unsubscribe",
        ),
        (
            EmailSubscriptionTypes.NEWSLETTER,
            "receive_newsletter",
            True,
            "newsletter-unsubscribe",
        ),
    ),
)
@pytest.mark.django_db
def test_unsubscribe_link(
    subscription_type,
    subscription_attr,
    subscription_preference,
    unsubscribe_viewname,
):
    user = UserFactory()
    setattr(user.user_profile, subscription_attr, subscription_preference)
    link = user.user_profile.get_unsubscribe_link(
        subscription_type=subscription_type
    )
    assert link == reverse(
        unsubscribe_viewname,
        kwargs={"token": user.user_profile.unsubscribe_token},
    )
