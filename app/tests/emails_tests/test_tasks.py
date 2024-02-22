import pytest
from django.contrib.sites.models import Site
from django.core import mail
from django.core.mail import get_connection

from grandchallenge.emails.emails import (
    create_email_object,
    send_standard_email_batch,
)
from grandchallenge.emails.tasks import get_receivers, send_bulk_email
from grandchallenge.emails.utils import SendActionChoices
from grandchallenge.profiles.models import EmailSubscriptionTypes
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.emails_tests.factories import EmailFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.parametrize(
    "factory,action",
    [
        (None, SendActionChoices.MAILING_LIST),
        (None, SendActionChoices.STAFF),
        (ChallengeFactory, SendActionChoices.CHALLENGE_ADMINS),
        (AlgorithmFactory, SendActionChoices.ALGORITHM_EDITORS),
        (ReaderStudyFactory, SendActionChoices.READER_STUDY_EDITORS),
    ],
)
@pytest.mark.django_db
def test_get_receivers(factory, action):
    u1, u2, u3, u4 = UserFactory.create_batch(4)
    u2.is_active = False
    u2.save()
    for user in [u1, u2]:
        user.user_profile.receive_newsletter = True
        user.user_profile.save()
        if action == SendActionChoices.STAFF:
            user.is_staff = True
            user.save()

    if factory == ChallengeFactory:
        obj = factory(creator=u1)
        obj2 = factory(creator=u2)
    elif factory in [AlgorithmFactory, ReaderStudyFactory]:
        obj = factory()
        obj2 = factory()
        obj.add_editor(u1)
        obj2.add_editor(u2)

    receivers = get_receivers(action)

    assert len(receivers) == 1
    for user in [u1]:
        assert user in receivers
    for user in [u2, u3, u4]:
        assert user not in receivers


@pytest.mark.django_db
def test_email_content(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    email = EmailFactory(subject="Test email", body="Test content")
    u1, u2 = UserFactory.create_batch(2)
    for user in [u1, u2]:
        user.user_profile.receive_newsletter = True
        user.user_profile.save()

    assert len(mail.outbox) == 0

    send_bulk_email(action=SendActionChoices.MAILING_LIST, email_pk=email.pk)

    assert len(mail.outbox) == 2
    email.refresh_from_db()
    assert email.sent

    for m in mail.outbox:
        assert (
            m.subject
            == f"[{Site.objects.get_current().domain.lower()}] Test email"
        )
        assert "Test content" in m.body
        if m.to == [u1.email]:
            assert reverse(
                "newsletter-unsubscribe",
                kwargs={"token": u1.user_profile.unsubscribe_token},
            ) in str(m.alternatives)
        else:
            assert reverse(
                "newsletter-unsubscribe",
                kwargs={"token": u2.user_profile.unsubscribe_token},
            ) in str(m.alternatives)

    # check that email sending task is idempotent
    mail.outbox.clear()
    send_bulk_email(action=SendActionChoices.MAILING_LIST, email_pk=email.pk)
    assert len(mail.outbox) == 0


@pytest.mark.parametrize(
    "subscription_type, unsubscribe_viewname",
    [
        (EmailSubscriptionTypes.NEWSLETTER, "newsletter-unsubscribe"),
        (EmailSubscriptionTypes.NOTIFICATION, "notification-unsubscribe"),
        (EmailSubscriptionTypes.SYSTEM, None),
    ],
)
@pytest.mark.django_db
def test_unsubscribe_headers(subscription_type, unsubscribe_viewname):
    user = UserFactory()
    user.user_profile.receive_newsletter = True
    user.user_profile.receive_notification_emails = True
    user.user_profile.save()
    site = Site.objects.get_current()

    if unsubscribe_viewname:
        unsubscribe_link = reverse(
            unsubscribe_viewname,
            kwargs={"token": user.user_profile.unsubscribe_token},
        )
    else:
        unsubscribe_link = None

    assert len(mail.outbox) == 0
    send_standard_email_batch(
        site=site,
        subject="Test",
        markdown_message="Some content",
        recipients=[user],
        subscription_type=subscription_type,
    )
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [user.email]
    if unsubscribe_link:
        assert unsubscribe_link in str(email.alternatives)
        assert email.extra_headers["List-Unsubscribe"] == unsubscribe_link
        assert (
            email.extra_headers["List-Unsubscribe-Post"]
            == "List-Unsubscribe=One-Click"
        )


@pytest.mark.parametrize(
    "subscription_type,expected_recipients",
    [
        (EmailSubscriptionTypes.NEWSLETTER, [True, False, True]),
        (EmailSubscriptionTypes.NOTIFICATION, [True, False, False]),
        (EmailSubscriptionTypes.SYSTEM, [True, True, True]),
    ],
)
@pytest.mark.django_db
def test_send_email_is_filtered(subscription_type, expected_recipients):
    inactive_user = UserFactory(is_active=False)
    u1, u2, u3 = UserFactory.create_batch(3)

    u1.user_profile.receive_newsletter = True
    u1.user_profile.receive_notification_emails = True
    u1.user_profile.save()

    u2.user_profile.receive_newsletter = False
    u2.user_profile.receive_notification_emails = False
    u2.user_profile.save()

    u3.user_profile.receive_newsletter = True
    u3.user_profile.receive_notification_emails = False
    u3.user_profile.save()

    send_standard_email_batch(
        recipients=[inactive_user, u1, u2, u3],
        subscription_type=subscription_type,
        markdown_message="foo",
        site=Site.objects.get_current(),
        subject="bar",
    )

    sent_emails = [email.to[0] for email in mail.outbox]

    expected_users = [
        user.email
        for boolean, user in zip(
            expected_recipients, [u1, u2, u3], strict=True
        )
        if boolean
    ]
    assert expected_users == sent_emails


@pytest.mark.parametrize(
    "subscription_type",
    [
        EmailSubscriptionTypes.NEWSLETTER,
        EmailSubscriptionTypes.NOTIFICATION,
        EmailSubscriptionTypes.SYSTEM,
    ],
)
@pytest.mark.django_db
def test_cannot_email_inactive_users(subscription_type):
    inactive_user = UserFactory(is_active=False)

    with pytest.raises(ValueError) as error:
        create_email_object(
            recipient=inactive_user,
            connection=get_connection(),
            site=Site.objects.get_current(),
            markdown_message="foo",
            subject="bar",
            subscription_type=subscription_type,
        )

    assert str(error.value) == "Inactive users cannot be emailed"


@pytest.mark.django_db
def test_can_always_email_system_messages():
    user = UserFactory(is_active=True)

    user.user_profile.receive_newsletter = True
    user.user_profile.receive_notification_emails = True
    user.user_profile.save()

    email = create_email_object(
        recipient=user,
        connection=get_connection(),
        site=Site.objects.get_current(),
        markdown_message="foo",
        subject="bar",
        subscription_type=EmailSubscriptionTypes.SYSTEM,
    )

    assert email


@pytest.mark.django_db
def test_can_email_newsletter_if_opted_in():
    user = UserFactory(is_active=True)

    user.user_profile.receive_newsletter = True
    user.user_profile.receive_notification_emails = False
    user.user_profile.save()

    email = create_email_object(
        recipient=user,
        connection=get_connection(),
        site=Site.objects.get_current(),
        markdown_message="foo",
        subject="bar",
        subscription_type=EmailSubscriptionTypes.NEWSLETTER,
    )

    assert email

    user.user_profile.receive_newsletter = False
    user.user_profile.save()

    with pytest.raises(ValueError) as error:
        create_email_object(
            recipient=user,
            connection=get_connection(),
            site=Site.objects.get_current(),
            markdown_message="foo",
            subject="bar",
            subscription_type=EmailSubscriptionTypes.NEWSLETTER,
        )

    assert str(error.value) == "User has opted out of newsletter emails"


@pytest.mark.django_db
def test_can_email_notification_if_opted_in():
    user = UserFactory(is_active=True)

    user.user_profile.receive_newsletter = False
    user.user_profile.receive_notification_emails = True
    user.user_profile.save()

    email = create_email_object(
        recipient=user,
        connection=get_connection(),
        site=Site.objects.get_current(),
        markdown_message="foo",
        subject="bar",
        subscription_type=EmailSubscriptionTypes.NOTIFICATION,
    )

    assert email

    user.user_profile.receive_notification_emails = False
    user.user_profile.save()

    with pytest.raises(ValueError) as error:
        create_email_object(
            recipient=user,
            connection=get_connection(),
            site=Site.objects.get_current(),
            markdown_message="foo",
            subject="bar",
            subscription_type=EmailSubscriptionTypes.NOTIFICATION,
        )

    assert str(error.value) == "User has opted out of notification emails"
