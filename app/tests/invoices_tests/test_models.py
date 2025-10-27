from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.challenges.models import Challenge
from grandchallenge.invoices.models import (
    PaymentStatusChoices,
    PaymentTypeChoices,
)
from tests.factories import ChallengeFactory
from tests.invoices_tests.factories import InvoiceFactory


@pytest.mark.django_db
def test_approved_compute_costs_euro_millicents_no_invoices():
    ChallengeFactory()
    expected_budget = 0

    challenge = Challenge.objects.with_available_compute().first()
    assert (
        challenge.approved_compute_costs_euro_millicents
        == expected_budget * 1000 * 100
    )


@pytest.mark.django_db
def test_approved_compute_costs_euro_millicents_paid_invoice():
    challenge = ChallengeFactory()
    expected_budget = 1

    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=expected_budget,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert (
        challenge.approved_compute_costs_euro_millicents
        == expected_budget * 1000 * 100
    )


@pytest.mark.django_db
def test_approved_compute_costs_euro_millicents_complimentary_invoices():
    challenge = ChallengeFactory()
    expected_budget = 20

    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert (
        challenge.approved_compute_costs_euro_millicents
        == expected_budget * 1000 * 100
    )


@pytest.mark.django_db
def test_approved_compute_costs_euro_millicents_filter_invoices():
    challenge = ChallengeFactory()
    expected_budget = 20

    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=50,
        compute_costs_euros=0,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=50,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.ISSUED,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=50,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.INITIALIZED,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=50,
        compute_costs_euros=expected_budget,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=50,
        compute_costs_euros=30,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.ISSUED,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=50,
        compute_costs_euros=0,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert (
        challenge.approved_compute_costs_euro_millicents
        == expected_budget * 1000 * 100
    )


@pytest.mark.django_db
def test_approved_compute_costs_postpaid_no_paid_invoices():
    InvoiceFactory(
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.POSTPAID,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 0


@pytest.mark.django_db
def test_approved_compute_costs_postpaid_with_paid_invoice():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.POSTPAID,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 2 * 1000 * 100


@pytest.mark.django_db
def test_approved_compute_costs_postpaid_paid():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
        payment_type=PaymentTypeChoices.POSTPAID,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 0 * 1000 * 100


@pytest.mark.django_db
def test_approved_compute_costs_postpaid_paid_with_paid_invoice():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
        payment_type=PaymentTypeChoices.POSTPAID,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 2 * 1000 * 100


@pytest.mark.django_db
def test_approved_compute_costs_postpaid_with_complimentary_invoice():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.POSTPAID,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 1 * 1000 * 100


@pytest.mark.django_db
def test_approved_compute_costs_with_paid_and_cancelled_invoice():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.CANCELLED,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 1 * 1000 * 100


@pytest.mark.django_db
def test_approved_compute_costs_postpaid_with_paid_and_cancelled_invoice():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.CANCELLED,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.POSTPAID,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 2 * 1000 * 100


@pytest.mark.django_db
def test_approved_compute_costs_postpaid_with_cancelled_invoice():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.CANCELLED,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_type=PaymentTypeChoices.POSTPAID,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 0 * 1000 * 100


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_status, required_field_name, field_value, expected_error_message",
    (
        (
            PaymentStatusChoices.ISSUED,
            "issued_on",
            None,
            "When setting the payment status to 'Issued', you must set the 'Issued on' date.",
        ),
        (
            PaymentStatusChoices.ISSUED,
            "internal_invoice_number",
            "",
            "When setting the payment status to 'Issued', you must specify the internal invoice number.",
        ),
        (
            PaymentStatusChoices.ISSUED,
            "internal_client_number",
            "",
            "When setting the payment status to 'Issued', you must specify the internal client number.",
        ),
        (
            PaymentStatusChoices.PAID,
            "paid_on",
            None,
            "When setting the payment status to 'Paid', you must set the 'Paid on' date.",
        ),
    ),
)
def test_payment_status_required_fields(
    payment_status, required_field_name, field_value, expected_error_message
):
    invoice = InvoiceFactory(
        payment_status=payment_status,
    )

    setattr(invoice, required_field_name, field_value)
    with pytest.raises(ValidationError) as e:
        invoice.full_clean()
    assert len(e.value.messages) == 1
    assert e.value.messages[0] == expected_error_message

    # should work with complimentary type
    invoice.payment_type = PaymentTypeChoices.COMPLIMENTARY
    invoice.save()


@pytest.mark.django_db
def test_payment_type_complimentary_requires_internal_comments():
    invoice = InvoiceFactory(
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )
    invoice.internal_comments = ""
    with pytest.raises(ValidationError) as e:
        invoice.full_clean()
    assert len(e.value.messages) == 1
    assert (
        "Please explain why the invoice is complimentary in the internal comments."
        == e.value.messages[0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_type", (PaymentTypeChoices.PREPAID, PaymentTypeChoices.POSTPAID)
)
@pytest.mark.parametrize(
    "required_field_name, expected_error_message",
    (
        (
            "contact_name",
            "Contact name is required for non-complimentary invoices.",
        ),
        (
            "contact_email",
            "Contact email is required for non-complimentary invoices.",
        ),
        (
            "billing_address",
            "Billing address is required for non-complimentary invoices.",
        ),
        (
            "vat_number",
            "VAT number is required for non-complimentary invoices.",
        ),
    ),
)
def test_payment_type_non_complimentary_requires_details(
    payment_type, required_field_name, expected_error_message
):
    invoice = InvoiceFactory()
    setattr(invoice, required_field_name, "")
    with pytest.raises(ValidationError) as e:
        invoice.full_clean()
    assert len(e.value.messages) == 1
    assert expected_error_message == e.value.messages[0]


@pytest.mark.parametrize(
    "payment_status",
    set(PaymentStatusChoices).difference([PaymentStatusChoices.INITIALIZED]),
)
@pytest.mark.django_db
def test_total_amount_cannot_change(payment_status):
    invoice = InvoiceFactory(
        payment_status=payment_status,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=2,
    )
    invoice.support_costs_euros = 1
    with pytest.raises(ValidationError) as e:
        invoice.clean()
    assert "The total amount may not change" in e.value.message

    invoice.storage_costs_euros = 1
    with nullcontext():
        invoice.clean()


@pytest.mark.django_db
def test_total_amount_can_change_for_initialized_payment_status():
    invoice = InvoiceFactory(
        payment_status=PaymentStatusChoices.INITIALIZED,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=2,
    )
    invoice.support_costs_euros = 1
    with nullcontext():
        invoice.clean()
