from unittest.mock import MagicMock, call
from zoneinfo import ZoneInfo

import pytest
from dateutil.utils import today
from django.core import mail
from django.utils.formats import date_format
from django.utils.timezone import datetime, now, timedelta

from grandchallenge.challenges.tasks import update_challenge_compute_costs
from grandchallenge.invoices.models import Invoice, PaymentStatusChoices
from grandchallenge.invoices.tasks import (
    send_challenge_invoice_issued_notification_emails,
    send_challenge_invoice_overdue_reminder_emails,
    send_open_invoices_email,
    send_post_paid_invoice_follow_up_emails,
)
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
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
            payment_status=Invoice.PaymentStatusChoices.PAID,
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
    "payment_type,payment_status",
    [
        (
            Invoice.PaymentTypeChoices.COMPLIMENTARY,
            Invoice.PaymentStatusChoices.PAID,
        ),
        (
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentStatusChoices.PAID,
        ),
        (
            Invoice.PaymentTypeChoices.POSTPAID,
            Invoice.PaymentStatusChoices.PAID,
        ),
        (
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentStatusChoices.INITIALIZED,
        ),
        (
            Invoice.PaymentTypeChoices.POSTPAID,
            Invoice.PaymentStatusChoices.INITIALIZED,
        ),
        (
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentStatusChoices.REQUESTED,
        ),
        (
            Invoice.PaymentTypeChoices.POSTPAID,
            Invoice.PaymentStatusChoices.REQUESTED,
        ),
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
    settings.LAMBDA_TASKS_EAGER = True

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
    settings.LAMBDA_TASKS_EAGER = True

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
def test_prepaid_invoice_paid_notification_emails_on_save(
    settings,
    django_capture_on_commit_callbacks,
):
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    contact_email = "contact_person@example.com"

    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=5000,
        compute_costs_euros=10,
        storage_costs_euros=5,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
        issued_on=datetime(2025, 2, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
        contact_email=contact_email,
        contact_name="John Doe",
    )

    # Clear outbox from the ISSUED notification sent on create
    mail.outbox.clear()

    invoice.payment_status = Invoice.PaymentStatusChoices.PAID
    invoice.paid_on = datetime(2025, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    with django_capture_on_commit_callbacks(execute=True):
        invoice.save()

    expected_subject = "[{challenge_name}] Invoice Payment Received".format(
        challenge_name=challenge.short_name,
    )

    organizer_mail = next(
        m for m in mail.outbox if challenge_admin.email in m.to
    )
    assert expected_subject in organizer_mail.subject
    assert "we have received payment" in organizer_mail.body
    assert challenge.short_name in organizer_mail.body
    assert "Compute capacity reservation: 10 Euro" in organizer_mail.body
    assert "Storage capacity reservation: 5 Euro" in organizer_mail.body
    assert "Base cost: 5000 Euro" in organizer_mail.body
    assert (
        "a compute budget of 10 Euro has become available"
        in organizer_mail.body
    )
    assert (
        "You can now use this budget to process submissions."
        in organizer_mail.body
    )

    contact_person_mail = next(m for m in mail.outbox if contact_email in m.to)
    assert expected_subject in contact_person_mail.subject
    assert "Dear John Doe" in contact_person_mail.body
    assert "we have received payment" in contact_person_mail.body
    assert (
        "You can now use this budget to process submissions."
        in contact_person_mail.body
    )


@pytest.mark.django_db
def test_prepaid_invoice_paid_email_without_compute_budget(
    settings,
    django_capture_on_commit_callbacks,
):
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    contact_email = "contact_person@example.com"

    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=0,
        storage_costs_euros=5,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
        issued_on=datetime(2025, 2, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
        contact_email=contact_email,
        contact_name="John Doe",
    )

    # Clear outbox from the ISSUED notification sent on create
    mail.outbox.clear()

    invoice.payment_status = Invoice.PaymentStatusChoices.PAID
    invoice.paid_on = datetime(2025, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    with django_capture_on_commit_callbacks(execute=True):
        invoice.save()

    organizer_mail = next(
        m for m in mail.outbox if challenge_admin.email in m.to
    )
    expected_subject = "[{challenge_name}] Invoice Payment Received".format(
        challenge_name=challenge.short_name,
    )
    assert expected_subject in organizer_mail.subject
    assert "we have received payment" in organizer_mail.body
    assert challenge.short_name in organizer_mail.body
    assert "Compute capacity reservation: 0 Euro" in organizer_mail.body
    assert "Storage capacity reservation: 5 Euro" in organizer_mail.body
    assert (
        "You can now use this budget to process submissions."
        not in organizer_mail.body
    )


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
    i6 = InvoiceFactory(payment_status=Invoice.PaymentStatusChoices.CANCELLED)
    i7 = InvoiceFactory(
        payment_status=Invoice.PaymentStatusChoices.PAID,
        payment_type=Invoice.PaymentTypeChoices.COMPLIMENTARY,
    )
    i8 = InvoiceFactory(
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
    assert str(i7) not in mail.outbox[0].body
    assert str(i8) not in mail.outbox[0].body


@pytest.mark.django_db
def test_send_open_invoices_email_not_sent_when_no_invoices(settings):
    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]

    InvoiceFactory(payment_status=Invoice.PaymentStatusChoices.PAID)
    InvoiceFactory(payment_status=Invoice.PaymentStatusChoices.CANCELLED)

    send_open_invoices_email()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_send_post_paid_invoice_follow_up_emails_content():
    challenge = ChallengeFactory()
    challenge_admin = challenge.creator
    contact_email = "contact_person@example.com"

    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on=today() + timedelta(days=1),
        contact_email=contact_email,
        contact_name="John Doe",
        billing_address="Some Street 12, 12345 SomeCity, SomeCountry",
        vat_number="12345",
    )

    send_post_paid_invoice_follow_up_emails()

    expected_subject = (
        "[{challenge_name}] Post-paid invoice date approaching".format(
            challenge_name=challenge.short_name,
        )
    )

    # challenge admin and invoice contact person are emailed
    assert len(mail.outbox) == 2
    for email in mail.outbox:
        assert expected_subject in email.subject
        assert date_format(invoice.follow_up_on, "F jS Y") in email.body
        assert invoice.billing_address in email.body
        assert invoice.contact_name in email.body
        assert invoice.contact_email in email.body
        assert invoice.vat_number in email.body

    recipient_emails = [email.to[0] for email in mail.outbox]
    assert challenge_admin.email in recipient_emails
    assert contact_email in recipient_emails


@pytest.mark.django_db
def test_send_post_paid_invoice_follow_up_emails_queryset(mocker):
    challenge = ChallengeFactory()

    postpaid_relevant = InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on=today() + timedelta(days=1),
    )
    # create a bunch of other invoices that should not trigger an email
    InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on=today() + timedelta(days=50),
    )
    InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.REQUESTED,
    )
    InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
    )
    InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
    )
    InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.COMPLIMENTARY,
    )

    mock_method = mocker.patch(
        "grandchallenge.invoices.tasks.send_postpaid_invoice_follow_up_date_approaching_email",
        return_value=MagicMock(),
    )

    send_post_paid_invoice_follow_up_emails()

    assert mock_method.call_count == 1
    mock_method.assert_has_calls(
        [
            call(postpaid_relevant),
        ],
    )


@pytest.mark.django_db
def test_invoice_budget_alert_email(
    settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory(short_name="test")
    challenge_admin = UserFactory()
    challenge.add_admin(challenge_admin)
    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]

    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
        internal_invoice_number="154040051",
    )
    phase = PhaseFactory(challenge=challenge)
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )

    evaluation.utilization.invoice = invoice
    evaluation.utilization.compute_cost_euro_millicents = 5 * 1000 * 100
    evaluation.utilization.save()

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    # Budget alert threshold not exceeded
    assert len(mail.outbox) == 0

    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.invoice = invoice
    evaluation.utilization.compute_cost_euro_millicents = 3 * 1000 * 100
    evaluation.utilization.save()

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    # Budget alert threshold exceeded
    assert len(mail.outbox) == 3
    recipients = {r for m in mail.outbox for r in m.to}
    assert recipients == {
        challenge.creator.email,
        challenge_admin.email,
        staff_user.email,
    }

    challenge_admin_email = [
        m for m in mail.outbox if challenge_admin.email in m.to
    ]
    assert (
        challenge_admin_email[0].subject
        == "[testserver] [test] over 70% Compute Budget Consumed Alert"
    )
    assert (
        "We would like to inform you that more than 70% of the compute budget "
        "for Prepaid invoice 154040051 of the test challenge has been used"
        in challenge_admin_email[0].body
    )

    mail.outbox.clear()
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.invoice = invoice
    evaluation.utilization.compute_cost_euro_millicents = 100000
    evaluation.utilization.save()

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    # Next budget alert threshold not exceeded
    assert len(mail.outbox) == 0

    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.invoice = invoice
    evaluation.utilization.compute_cost_euro_millicents = 1
    evaluation.utilization.save()

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    # Next budget alert threshold exceeded
    assert len(mail.outbox) != 0
    assert (
        mail.outbox[0].subject
        == "[testserver] [test] over 90% Compute Budget Consumed Alert"
    )


@pytest.mark.django_db
def test_invoice_budget_alert_two_thresholds_one_email(
    settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory(short_name="test")

    assert challenge.percent_budget_consumed_warning_thresholds == [
        70,
        90,
        100,
    ]

    challenge_admin = UserFactory()
    challenge.add_admin(challenge_admin)
    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]
    invoice = InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    phase = PhaseFactory(challenge=challenge)
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.invoice = invoice
    evaluation.utilization.compute_cost_euro_millicents = 950000
    evaluation.utilization.save()

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    # Two budget alert thresholds exceeded, alert only sent for last one.
    assert len(mail.outbox) == 3
    recipients = {r for m in mail.outbox for r in m.to}
    assert recipients == {
        challenge.creator.email,
        challenge_admin.email,
        staff_user.email,
    }
    assert (
        mail.outbox[0].subject
        == "[testserver] [test] over 90% Compute Budget Consumed Alert"
    )


@pytest.mark.django_db
def test_invoice_budget_alert_no_budget(
    settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory()
    phase = PhaseFactory(challenge=challenge)
    invoice = InvoiceFactory(challenge=challenge, compute_costs_euros=0)
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.invoice = invoice
    evaluation.utilization.compute_cost_euro_millicents = 1
    evaluation.utilization.save()

    assert len(mail.outbox) == 0

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    assert len(mail.outbox) != 0
    assert "Budget Consumed Alert" in mail.outbox[0].subject
