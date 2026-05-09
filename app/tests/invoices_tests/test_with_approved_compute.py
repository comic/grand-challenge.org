from datetime import timedelta

import pytest
from django.utils.timezone import now

from grandchallenge.invoices.models import (
    Invoice,
    PaymentStatusChoices,
    PaymentTypeChoices,
)
from tests.factories import ChallengeFactory
from tests.invoices_tests.factories import InvoiceFactory


##########
# PREPAID
#########
@pytest.mark.django_db
def test_prepaid_available():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 1 * 1000 * 100


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_status",
    (
        PaymentStatusChoices.INITIALIZED,
        PaymentStatusChoices.REQUESTED,
        PaymentStatusChoices.ISSUED,
        PaymentStatusChoices.CANCELLED,
    ),
)
def test_prepaid_unavailable(payment_status):
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=payment_status,
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 0


@pytest.mark.django_db
def test_prepaid_available_but_utilized():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 4 * 1000 * 100


@pytest.mark.django_db
def test_prepaid_available_utilized_but_expired():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=now() - timedelta(days=2),
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 1 * 1000 * 100


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_status",
    (
        PaymentStatusChoices.INITIALIZED,
        PaymentStatusChoices.REQUESTED,
        PaymentStatusChoices.ISSUED,
        PaymentStatusChoices.CANCELLED,
    ),
)
def test_prepaid_unavailable_but_utilized_but_expired(payment_status):
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=payment_status,
        expires_on=now() - timedelta(days=2),
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 0


##########
# POSTPAID
#########


@pytest.mark.parametrize(
    "prepaid_payment_status,postpaid_payment_status",
    (
        (PaymentStatusChoices.PAID, PaymentStatusChoices.INITIALIZED),
        (PaymentStatusChoices.PAID, PaymentStatusChoices.REQUESTED),
        (PaymentStatusChoices.PAID, PaymentStatusChoices.ISSUED),
        (PaymentStatusChoices.PAID, PaymentStatusChoices.PAID),
        (None, PaymentStatusChoices.PAID),
    ),
)
@pytest.mark.django_db
def test_postpaid_available(prepaid_payment_status, postpaid_payment_status):
    challenge = ChallengeFactory()
    if prepaid_payment_status is not None:
        InvoiceFactory(
            challenge=challenge,
            compute_costs_euros=1,
            utilized_compute_cost_euro_millicents=0,
            payment_type=PaymentTypeChoices.PREPAID,
            payment_status=prepaid_payment_status,
        )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=2,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=postpaid_payment_status,
    )

    invoices = challenge.invoices.with_available_compute()
    assert (
        invoices.get(pk=postpaid_invoice.pk).approved_compute_euros_millicents
        == 2 * 1000 * 100
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "prepaid_payment_status, postpaid_payment_status",
    (
        (
            PaymentStatusChoices.PAID,
            PaymentStatusChoices.CANCELLED,
        ),
        (
            PaymentStatusChoices.INITIALIZED,
            PaymentStatusChoices.INITIALIZED,
        ),
        (
            PaymentStatusChoices.INITIALIZED,
            PaymentStatusChoices.REQUESTED,
        ),
        (
            PaymentStatusChoices.INITIALIZED,
            PaymentStatusChoices.ISSUED,
        ),
        (
            PaymentStatusChoices.INITIALIZED,
            PaymentStatusChoices.CANCELLED,
        ),
        (
            PaymentStatusChoices.REQUESTED,
            PaymentStatusChoices.INITIALIZED,
        ),
        (
            PaymentStatusChoices.REQUESTED,
            PaymentStatusChoices.REQUESTED,
        ),
        (
            PaymentStatusChoices.REQUESTED,
            PaymentStatusChoices.ISSUED,
        ),
        (
            PaymentStatusChoices.REQUESTED,
            PaymentStatusChoices.CANCELLED,
        ),
        (
            PaymentStatusChoices.ISSUED,
            PaymentStatusChoices.INITIALIZED,
        ),
        (
            PaymentStatusChoices.ISSUED,
            PaymentStatusChoices.REQUESTED,
        ),
        (
            PaymentStatusChoices.ISSUED,
            PaymentStatusChoices.ISSUED,
        ),
        (
            PaymentStatusChoices.ISSUED,
            PaymentStatusChoices.CANCELLED,
        ),
        (
            PaymentStatusChoices.CANCELLED,
            PaymentStatusChoices.INITIALIZED,
        ),
        (
            PaymentStatusChoices.CANCELLED,
            PaymentStatusChoices.REQUESTED,
        ),
        (
            PaymentStatusChoices.CANCELLED,
            PaymentStatusChoices.ISSUED,
        ),
        (
            PaymentStatusChoices.CANCELLED,
            PaymentStatusChoices.CANCELLED,
        ),
    ),
)
def test_postpaid_unavailable(prepaid_payment_status, postpaid_payment_status):
    challenge = ChallengeFactory()
    if prepaid_payment_status is not None:
        InvoiceFactory(
            challenge=challenge,
            compute_costs_euros=1,
            utilized_compute_cost_euro_millicents=0,
            payment_type=PaymentTypeChoices.PREPAID,
            payment_status=prepaid_payment_status,
        )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=2,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=postpaid_payment_status,
    )

    invoices = challenge.invoices.with_available_compute()
    assert (
        invoices.get(pk=postpaid_invoice.pk).approved_compute_euros_millicents
        == 0
    )


@pytest.mark.django_db
def test_postpaid_available_with_expired_paid_prepaid():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=now() - timedelta(days=2),
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=2,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=PaymentStatusChoices.INITIALIZED,
    )

    invoices = challenge.invoices.with_available_compute()
    assert (
        invoices.get(pk=postpaid_invoice.pk).approved_compute_euros_millicents
        == 2 * 1000 * 100
    )


@pytest.mark.django_db
def test_postpaid_available_but_utilized():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    invoices = challenge.invoices.with_available_compute()
    assert (
        invoices.get(pk=postpaid_invoice.pk).approved_compute_euros_millicents
        == 4 * 1000 * 100
    )


@pytest.mark.django_db
def test_postpaid_available_but_utilized_but_expired():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    invoices = challenge.invoices.with_available_compute()
    assert (
        invoices.get(pk=postpaid_invoice.pk).approved_compute_euros_millicents
        == 1 * 1000 * 100
    )


@pytest.mark.django_db
def test_postpaid_unavailable_but_utilized_but_expired():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.CANCELLED,
    )

    invoices = challenge.invoices.with_available_compute()
    assert (
        invoices.get(pk=postpaid_invoice.pk).approved_compute_euros_millicents
        == 0
    )


##########
# COMPLIMENTARY
#########


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_status",
    (
        PaymentStatusChoices.INITIALIZED,
        PaymentStatusChoices.REQUESTED,
        PaymentStatusChoices.ISSUED,
        PaymentStatusChoices.PAID,
    ),
)
def test_complimentary_available(payment_status):
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=payment_status,
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 1 * 1000 * 100


@pytest.mark.django_db
def test_complimentary_unavailable():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        utilized_compute_cost_euro_millicents=0,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=PaymentStatusChoices.CANCELLED,
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_status",
    (
        PaymentStatusChoices.INITIALIZED,
        PaymentStatusChoices.REQUESTED,
        PaymentStatusChoices.ISSUED,
        PaymentStatusChoices.PAID,
    ),
)
def test_complimentary_available_but_utilized(payment_status):
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=payment_status,
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 4 * 1000 * 100


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_status",
    (
        PaymentStatusChoices.INITIALIZED,
        PaymentStatusChoices.REQUESTED,
        PaymentStatusChoices.ISSUED,
        PaymentStatusChoices.PAID,
    ),
)
def test_complimentary_available_but_utilized_but_expired(payment_status):
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=payment_status,
        expires_on=now() - timedelta(days=2),
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 1 * 1000 * 100


@pytest.mark.django_db
def test_complimentary_unavailable_but_utilized_but_expired():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        utilized_compute_cost_euro_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=PaymentStatusChoices.CANCELLED,
        expires_on=now() - timedelta(days=2),
    )

    invoices = challenge.invoices.with_available_compute()
    assert invoices.get().approved_compute_euros_millicents == 0
