from contextlib import nullcontext

import pytest
from actstream.actions import follow
from django.contrib.sites.models import Site
from django.core import mail

from grandchallenge.components.models import ComponentInterface
from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.models import (
    EmailSubscriptionTypes,
    NotificationEmailOptions,
)
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
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


@pytest.mark.django_db
def test_file_civs_user_has_permission_to_use():
    user = UserFactory()
    assert list(user.user_profile.file_civs_user_has_permission_to_use) == []

    ci_file = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.ANY, store_in_database=False
    )
    ci_str = ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING)

    civ1, civ2, civ3, civ4, civ5, civ6 = (
        ComponentInterfaceValueFactory.create_batch(6, interface=ci_file)
    )
    civ_str = ComponentInterfaceValueFactory(interface=ci_str)

    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)

    job_with_perm.inputs.set([civ1])
    job_without_perm.inputs.set([civ2])

    rs = ReaderStudyFactory()
    rs.add_editor(user)
    ds_with_perm = DisplaySetFactory(reader_study=rs)
    ds_without_perm = DisplaySetFactory()

    ds_with_perm.values.set([civ3])
    ds_without_perm.values.set([civ4])

    archive = ArchiveFactory()
    archive.add_editor(user)
    ai_with_perm = ArchiveItemFactory(archive=archive)
    ai_without_perm = ArchiveItemFactory()

    ai_with_perm.values.set([civ5])
    ai_without_perm.values.set([civ6])

    del user.user_profile.file_civs_user_has_permission_to_use
    assert civ1 in user.user_profile.file_civs_user_has_permission_to_use
    assert civ3 in user.user_profile.file_civs_user_has_permission_to_use
    assert civ5 in user.user_profile.file_civs_user_has_permission_to_use
    assert civ2 not in user.user_profile.file_civs_user_has_permission_to_use
    assert civ4 not in user.user_profile.file_civs_user_has_permission_to_use
    assert civ6 not in user.user_profile.file_civs_user_has_permission_to_use
    assert (
        civ_str not in user.user_profile.file_civs_user_has_permission_to_use
    )
