from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.utils.timezone import datetime, now, timedelta

from grandchallenge.invoices.models import Invoice
from grandchallenge.invoices.tasks import (
    send_challenge_invoice_issued_notification_emails,
    send_challenge_invoice_overdue_reminder_emails,
    send_open_invoices_email,
)
from tests.factories import ChallengeFactory, UserFactory
from tests.invoices_tests.factories import InvoiceFactory

_fixed_now = datetime(2025, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invoice_kwargs",
    [
        # Case: invoice due
        dict(
            payment_type=Invoice.PaymentTypeChoices.PREPAID,
            payment_status=Invoice.PaymentStatusChoices.ISSUED,
            issued_on=_fixed_now - timedelta(weeks=5),
        ),
        # Case: postpaid invoice due
        dict(
            payment_type=Invoice.PaymentTypeChoices.POSTPAID,
            payment_status=Invoice.PaymentStatusChoices.ISSUED,
            issued_on=_fixed_now - timedelta(weeks=5),
        ),
    ],
)
def test_challenge_invoice_overdue_reminder_emails_sent(
    invoice_kwargs,
    settings,
    mocker,
):
    challenge = ChallengeFactory()
    challenge_admin = UserFactory()
    challenge.add_admin(challenge_admin)

    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]

    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        **invoice_kwargs,
    )

    mocker.patch(
        "grandchallenge.invoices.models.now",
        return_value=_fixed_now,
    )

    send_challenge_invoice_overdue_reminder_emails()

    expected_subject = (
        "[{challenge_name}] Outstanding Invoice Reminder".format(
            challenge_name=challenge.short_name,
        )
    )

    expected_body_organizer = (
        "we have an outstanding invoice for {amount} Euro".format(
            amount=invoice.total_amount_euros,
        )
    )

    staff_email = next(m for m in mail.outbox if staff_user.email in m.to)
    assert expected_subject in staff_email.subject

    organizer_mail = next(
        m for m in mail.outbox if challenge_admin.email in m.to
    )
    assert expected_subject in organizer_mail.subject
    assert expected_body_organizer in organizer_mail.body


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invoice_kwargs",
    [
        # Case: invoice due, but not overdue
        dict(
            payment_type=Invoice.PaymentTypeChoices.PREPAID,
            payment_status=Invoice.PaymentStatusChoices.ISSUED,
            issued_on=_fixed_now - timedelta(weeks=2),
        ),
        # Case: invoice issued, but of complimentary type
        dict(
            payment_type=Invoice.PaymentTypeChoices.COMPLIMENTARY,
            payment_status=Invoice.PaymentStatusChoices.ISSUED,
            issued_on=_fixed_now - timedelta(weeks=5),
        ),
    ],
)
def test_challenge_invoice_not_overdue_reminder_emails_not_send(
    invoice_kwargs,
    settings,
    mocker,
):
    challenge = ChallengeFactory()
    challenge_admin = UserFactory()
    challenge.add_admin(challenge_admin)

    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]

    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        **invoice_kwargs,
    )

    mocker.patch(
        "grandchallenge.invoices.models.now",
        return_value=_fixed_now,
    )

    send_challenge_invoice_overdue_reminder_emails()

    assert not any(staff_user.email in m.to for m in mail.outbox)
    assert not any(challenge_admin.email in m.to for m in mail.outbox)


@pytest.mark.django_db
def test_no_invoices_reminder_emails_not_send():
    send_challenge_invoice_overdue_reminder_emails()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_type",
    [
        Invoice.PaymentTypeChoices.COMPLIMENTARY,
        Invoice.PaymentTypeChoices.PREPAID,
        Invoice.PaymentTypeChoices.POSTPAID,
    ],
)
@pytest.mark.parametrize(
    "payment_status",
    [
        Invoice.PaymentStatusChoices.INITIALIZED,
        Invoice.PaymentStatusChoices.REQUESTED,
        Invoice.PaymentStatusChoices.PAID,
    ],
)
def test_challenge_invoice_overdue_reminder_emails_not_sent(
    payment_type,
    payment_status,
    settings,
    mocker,
):
    challenge = ChallengeFactory()
    challenge_admin = UserFactory()
    challenge.add_admin(challenge_admin)

    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]

    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_type=payment_type,
        payment_status=payment_status,
        issued_on=_fixed_now - timedelta(weeks=5),
    )

    mocker.patch(
        "grandchallenge.invoices.models.now",
        return_value=_fixed_now,
    )

    send_challenge_invoice_overdue_reminder_emails()

    assert not any(staff_user.email in m.to for m in mail.outbox)
    assert not any(challenge_admin.email in m.to for m in mail.outbox)


@pytest.mark.django_db
def test_challenge_invoice_overdue_reminder_emails_contact_person(mocker):
    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    contact_email = "contact_person@example.com"

    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
        issued_on=_fixed_now - timedelta(weeks=5),
        contact_email=contact_email,
        contact_name="John Doe",
    )

    mocker.patch(
        "grandchallenge.invoices.models.now",
        return_value=_fixed_now,
    )

    send_challenge_invoice_overdue_reminder_emails()

    expected_subject = (
        "[{challenge_name}] Outstanding Invoice Reminder".format(
            challenge_name=challenge.short_name,
        )
    )

    expected_body_organizer = (
        "we have an outstanding invoice for {amount} Euro".format(
            amount=invoice.total_amount_euros,
        )
    )

    organizer_mail = next(
        m for m in mail.outbox if challenge_admin.email in m.to
    )
    assert expected_subject in organizer_mail.subject
    assert expected_body_organizer in organizer_mail.body

    contact_person_mail = next(m for m in mail.outbox if contact_email in m.to)
    assert expected_subject in contact_person_mail.subject
    assert "Dear John Doe" in contact_person_mail.body
    assert expected_body_organizer in contact_person_mail.body


@pytest.mark.django_db
def test_challenge_invoice_issued_notification_emails():
    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    contact_email = "contact_person@example.com"

    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
        issued_on=datetime(2025, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
        contact_email=contact_email,
        contact_name="John Doe",
    )

    send_challenge_invoice_issued_notification_emails(pk=invoice.pk)

    expected_subject = "[{challenge_name}] Invoice Issued Notification".format(
        challenge_name=challenge.short_name,
    )

    expected_body = (
        "We would like to inform you that an invoice has been issued on March 1, 2025 "
        "for your challenge {challenge_name}.".format(
            challenge_name=challenge.short_name,
        )
    )

    organizer_mail = next(
        m for m in mail.outbox if challenge_admin.email in m.to
    )
    assert expected_subject in organizer_mail.subject
    assert expected_body in organizer_mail.body

    contact_person_mail = next(m for m in mail.outbox if contact_email in m.to)
    assert expected_subject in contact_person_mail.subject
    assert "Dear John Doe" in contact_person_mail.body
    assert expected_body in contact_person_mail.body


@pytest.mark.django_db
def test_challenge_invoice_issued_notification_emails_on_save(
    settings,
    django_capture_on_commit_callbacks,
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    contact_email = "contact_person@example.com"

    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        contact_email=contact_email,
        contact_name="John Doe",
    )

    assert not any(challenge_admin.email in m.to for m in mail.outbox)
    assert not any(contact_email in m.to for m in mail.outbox)

    invoice.payment_status = Invoice.PaymentStatusChoices.ISSUED
    invoice.issued_on = datetime(2025, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    with django_capture_on_commit_callbacks(execute=True):
        invoice.save()

    expected_subject = "[{challenge_name}] Invoice Issued Notification".format(
        challenge_name=challenge.short_name,
    )

    expected_body = (
        "We would like to inform you that an invoice has been issued on March 1, 2025 "
        "for your challenge {challenge_name}.".format(
            challenge_name=challenge.short_name,
        )
    )

    organizer_mail = next(
        m for m in mail.outbox if challenge_admin.email in m.to
    )
    assert expected_subject in organizer_mail.subject
    assert expected_body in organizer_mail.body

    contact_person_mail = next(m for m in mail.outbox if contact_email in m.to)
    assert expected_subject in contact_person_mail.subject
    assert "Dear John Doe" in contact_person_mail.body
    assert expected_body in contact_person_mail.body


@pytest.mark.django_db
def test_challenge_invoice_issued_notification_emails_on_create(
    settings,
    django_capture_on_commit_callbacks,
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    contact_email = "contact_person@example.com"

    with django_capture_on_commit_callbacks(execute=True):
        InvoiceFactory(
            challenge=challenge,
            support_costs_euros=0,
            compute_costs_euros=10,
            storage_costs_euros=0,
            payment_type=Invoice.PaymentTypeChoices.PREPAID,
            payment_status=Invoice.PaymentStatusChoices.ISSUED,
            issued_on=datetime(2025, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
            contact_email=contact_email,
            contact_name="John Doe",
        )

    assert len(mail.outbox) > 0

    expected_subject = "[{challenge_name}] Invoice Issued Notification".format(
        challenge_name=challenge.short_name,
    )

    expected_body = (
        "We would like to inform you that an invoice has been issued on March 1, 2025 "
        "for your challenge {challenge_name}.".format(
            challenge_name=challenge.short_name,
        )
    )

    organizer_mail = next(
        m for m in mail.outbox if challenge_admin.email in m.to
    )
    assert expected_subject in organizer_mail.subject
    assert expected_body in organizer_mail.body

    contact_person_mail = next(m for m in mail.outbox if contact_email in m.to)
    assert expected_subject in contact_person_mail.subject
    assert "Dear John Doe" in contact_person_mail.body
    assert expected_body in contact_person_mail.body


@pytest.mark.django_db
def test_send_open_invoices_email(settings):
    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]

    i1 = InvoiceFactory(
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on=now().date() - timedelta(days=1),
    )
    i2 = InvoiceFactory(
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
    )
    i3 = InvoiceFactory(
        payment_status=Invoice.PaymentStatusChoices.REQUESTED,
    )
    i4 = InvoiceFactory(
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
    )
    i5 = InvoiceFactory(payment_status=Invoice.PaymentStatusChoices.PAID)
    i6 = InvoiceFactory(
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on=now().date() + timedelta(days=30),
    )

    send_open_invoices_email()

    assert len(mail.outbox) == 1

    assert "Invoices to check" in mail.outbox[0].subject
    assert mail.outbox[0].to == [staff_user.email]
    assert str(i1) in mail.outbox[0].body
    assert str(i2) in mail.outbox[0].body
    assert str(i3) in mail.outbox[0].body
    assert str(i4) in mail.outbox[0].body
    assert str(i5) not in mail.outbox[0].body
    assert str(i6) not in mail.outbox[0].body
