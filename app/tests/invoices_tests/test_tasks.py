from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.utils.timezone import datetime, timedelta

from grandchallenge.invoices.models import Invoice
from grandchallenge.invoices.tasks import (
    send_challenge_outstanding_invoice_reminder_emails,
)
from tests.factories import ChallengeFactory, UserFactory
from tests.invoices_tests.factories import InvoiceFactory

_fixed_now = datetime(2025, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invoice_kwargs, send_email",
    [
        (  # Case: no invoices
            {},
            False,
        ),
        (  # Case: invoice, but of complimentary type
            dict(
                payment_type=Invoice.PaymentTypeChoices.COMPLIMENTARY,
                payment_status=Invoice.PaymentStatusChoices.ISSUED,
            ),
            False,
        ),
        (  # Case: invoice, but not long outstanding
            dict(
                payment_type=Invoice.PaymentTypeChoices.PREPAID,
                payment_status=Invoice.PaymentStatusChoices.ISSUED,
                issued_on=_fixed_now - timedelta(weeks=2),
            ),
            False,
        ),
        (  # Case: invoice outstanding
            dict(
                payment_type=Invoice.PaymentTypeChoices.PREPAID,
                payment_status=Invoice.PaymentStatusChoices.ISSUED,
                issued_on=_fixed_now - timedelta(weeks=5),
            ),
            True,
        ),
    ],
)
def test_challenge_outstanding_invoice_reminder_emails(
    invoice_kwargs,
    send_email,
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
        "grandchallenge.invoices.tasks.now",
        return_value=_fixed_now,
    )

    send_challenge_outstanding_invoice_reminder_emails()

    if send_email:
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
    else:
        assert not any(staff_user.email in m.to for m in mail.outbox)
        assert not any(challenge_admin.email in m.to for m in mail.outbox)


@pytest.mark.django_db
def test_challenge_outstanding_invoice_reminder_emails_contact_person(mocker):
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
        "grandchallenge.invoices.tasks.now",
        return_value=_fixed_now,
    )

    send_challenge_outstanding_invoice_reminder_emails()

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
