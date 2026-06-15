from contextlib import nullcontext
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import pytest
from dateutil.utils import today
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import datetime, now

from grandchallenge.challenges.models import Challenge
from grandchallenge.invoices.models import (
    Invoice,
    PaymentStatusChoices,
    PaymentTypeChoices,
)
from tests.factories import ChallengeFactory
from tests.invoices_tests.factories import InvoiceFactory


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
    "payment_status, context",
    (
        (PaymentStatusChoices.PAID, nullcontext()),
        (PaymentStatusChoices.CANCELLED, nullcontext()),
        (
            PaymentStatusChoices.ISSUED,
            pytest.raises(
                ValidationError,
                match="Complimentary invoices must have a 'Paid' or 'Cancelled' status.",
            ),
        ),
        (
            PaymentStatusChoices.INITIALIZED,
            pytest.raises(
                ValidationError,
                match="Complimentary invoices must have a 'Paid' or 'Cancelled' status.",
            ),
        ),
        (
            PaymentStatusChoices.REQUESTED,
            pytest.raises(
                ValidationError,
                match="Complimentary invoices must have a 'Paid' or 'Cancelled' status.",
            ),
        ),
    ),
)
def test_payment_type_complimentary_requires_paid_or_cancelled(
    payment_status, context
):
    invoice = InvoiceFactory(
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )
    invoice.payment_status = payment_status
    with context:
        invoice.full_clean()


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
@pytest.mark.parametrize(
    "payment_type", (PaymentTypeChoices.PREPAID, PaymentTypeChoices.POSTPAID)
)
@pytest.mark.django_db
def test_total_amount_cannot_change(payment_status, payment_type):
    invoice = InvoiceFactory(
        payment_type=payment_type,
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


@pytest.mark.django_db
def test_total_amount_can_change_for_complimentary_invoices():
    invoice = InvoiceFactory(
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=2,
    )
    invoice.support_costs_euros = 1
    with nullcontext():
        invoice.clean()


@pytest.mark.parametrize(
    "payment_type", (PaymentTypeChoices.PREPAID, PaymentTypeChoices.POSTPAID)
)
@pytest.mark.django_db
def test_updating_total_amount_and_status_simultaneously_is_possible(
    payment_type,
):
    invoice = InvoiceFactory(
        payment_type=payment_type,
        payment_status=PaymentStatusChoices.INITIALIZED,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=2,
    )
    invoice.support_costs_euros = 2
    invoice.payment_status = PaymentStatusChoices.REQUESTED
    with nullcontext():
        invoice.clean()


@pytest.mark.django_db
def test_invoices_cannot_be_deleted():
    invoice = InvoiceFactory()

    with pytest.raises(ValidationError):
        invoice.delete()

    assert Invoice.objects.filter(pk=invoice.pk).exists()

    with pytest.raises(ValidationError):
        Invoice.objects.filter(pk=invoice.pk).delete()

    assert Invoice.objects.filter(pk=invoice.pk).exists()


@pytest.mark.django_db
def test_invoice_default_expires_on(settings, mocker):
    assert (
        settings.CHALLENGE_INVOICES_DEFAULT_EXPIRE_AFTER_YEARS
    ), "Setting exists"

    settings.CHALLENGE_INVOICES_DEFAULT_EXPIRE_AFTER_YEARS = 2

    fixed_now = datetime(2025, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
    mocker.patch(
        "grandchallenge.invoices.models.now",
        return_value=fixed_now,
    )
    invoice = InvoiceFactory()
    assert invoice.expires_on == date(2027, 3, 1)


@pytest.mark.django_db
def test_follow_up_on_valid():
    invoice = InvoiceFactory()
    invoice.follow_up_on = today() + timedelta(days=30)
    invoice.full_clean()


@pytest.mark.django_db
def test_follow_up_on_before_expires_on():
    invoice = InvoiceFactory()
    invoice.follow_up_on = today() + timedelta(days=30)
    invoice.expires_on = today() + timedelta(days=20)
    with pytest.raises(ValidationError) as e:
        invoice.full_clean()
    assert len(e.value.messages) == 1
    assert (
        "Follow-up date must be before the expiry date." == e.value.messages[0]
    )


@pytest.mark.django_db
def test_follow_up_on_not_more_than_year_in_future():
    invoice = InvoiceFactory()
    invoice.follow_up_on = today() + timedelta(days=2 * 365)
    with pytest.raises(ValidationError) as e:
        invoice.full_clean()
    assert len(e.value.messages) == 1
    assert (
        "Follow-up date cannot be more than a year into the future."
        == e.value.messages[0]
    )


@pytest.mark.django_db
def test_follow_up_on_required_for_initialized_postpaid():
    invoice = InvoiceFactory()
    invoice.payment_type = PaymentTypeChoices.POSTPAID
    invoice.payment_status = PaymentStatusChoices.INITIALIZED
    with pytest.raises(ValidationError) as e:
        invoice.full_clean()
    assert len(e.value.messages) == 1
    assert (
        "Follow-up date is required for initialized post-paid invoices."
        == e.value.messages[0]
    )

    # post-paid invoices in other states are fine without a follow-up date
    invoice2 = InvoiceFactory(payment_type=PaymentTypeChoices.POSTPAID)
    invoice2.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invoice_kwargs, badge",
    (
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
            ),
            '<span class="badge badge-info">Initialized</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.REQUESTED,
            ),
            '<span class="badge badge-info">Initialized</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.ISSUED,
                issued_on=now() + timedelta(days=1),
            ),
            '<span class="badge badge-info">Invoice Issued</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.CANCELLED,
            ),
            '<span class="badge badge-danger">Cancelled</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.PAID,
            ),
            '<span class="badge badge-success">Paid</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
                expires_on=now().date() - timedelta(days=7),
                follow_up_on=now().date() - timedelta(days=30),
            ),
            '<span class="badge badge-danger">Expired</span>',
        ),
    ),
)
def test_prepaid_invoice_status_badge(invoice_kwargs, badge):
    invoice = InvoiceFactory(
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        **invoice_kwargs,
    )
    invoice = Invoice.objects.with_is_expired().get(pk=invoice.pk)
    assert invoice.get_status_badge() == badge


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invoice_kwargs, badge",
    (
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
            ),
            '<span class="badge badge-success">Reserved</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.REQUESTED,
            ),
            '<span class="badge badge-success">Reserved</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.ISSUED,
                issued_on=now() + timedelta(days=1),
            ),
            '<span class="badge badge-success">Invoice Issued</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.CANCELLED,
            ),
            '<span class="badge badge-danger">Cancelled</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.PAID,
            ),
            '<span class="badge badge-success">Paid</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
                expires_on=now().date() - timedelta(days=7),
                follow_up_on=now().date() - timedelta(days=30),
            ),
            '<span class="badge badge-danger">Expired</span>',
        ),
    ),
)
def test_postpaid_invoice_status_badge(invoice_kwargs, badge):
    invoice = InvoiceFactory(
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        **invoice_kwargs,
    )
    invoice = Invoice.objects.with_is_expired().get(pk=invoice.pk)
    assert invoice.get_status_badge() == badge


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invoice_kwargs, badge",
    (
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.CANCELLED,
            ),
            '<span class="badge badge-danger">Cancelled</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.PAID,
            ),
            '<span class="badge badge-success">Paid</span>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.PAID,
                expires_on=now().date() - timedelta(days=7),
                follow_up_on=now().date() - timedelta(days=30),
            ),
            '<span class="badge badge-danger">Expired</span>',
        ),
    ),
)
def test_complimentary_invoice_status_badge(invoice_kwargs, badge):
    invoice = InvoiceFactory(
        payment_type=Invoice.PaymentTypeChoices.COMPLIMENTARY,
        **invoice_kwargs,
    )
    invoice = Invoice.objects.with_is_expired().get(pk=invoice.pk)
    assert invoice.get_status_badge() == badge


@pytest.mark.django_db
def test_postpaid_suggested_costs_properties():
    challenge = ChallengeFactory(
        size_in_storage=30 * 1024**3,
        size_in_registry=70 * 1024**3,
    )
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        storage_costs_euros=100,
        compute_cost_euro_millicents=110 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=PaymentStatusChoices.PAID,
    )
    # Postpaid invoice (initialized)
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=50,
        storage_costs_euros=0,
        compute_cost_euro_millicents=30 * 1000 * 100,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=PaymentStatusChoices.INITIALIZED,
    )
    postpaid_invoice = (
        Invoice.objects.prefetch_related(
            models.Prefetch(
                "challenge",
                queryset=Challenge.objects.with_invoices_with_budget_authorization(),
            )
        )
        .with_budget_authorization()
        .get(pk=postpaid_invoice.pk)
    )

    assert postpaid_invoice.total_unpaid_costs_euros == 30
    assert postpaid_invoice.suggested_total_postpaid_amount == 250
    assert postpaid_invoice.surplus == 220
    assert postpaid_invoice.suggested_compute_cost_euros == 179
    assert postpaid_invoice.suggested_storage_cost_euros == 71
