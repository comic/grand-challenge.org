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
def test_prepaid_no_utilization_positive_balance():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=2,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    assert invoice.compute_costs_balance_euros_millicents == 2 * 1000 * 100


@pytest.mark.django_db
def test_prepaid_utilization_positive_balance():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=2,
        compute_costs_utilized_euros_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    assert invoice.compute_costs_balance_euros_millicents == 1 * 1000 * 100


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
@pytest.mark.parametrize(
    "expires_on",
    (
        now() + timedelta(days=2),  # Not expired
        now() - timedelta(days=2),  # Expired
    ),
)
def test_prepaid_no_utilization_zero_balance(payment_status, expires_on):
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=payment_status,
        expires_on=expires_on,
    )
    assert invoice.compute_costs_balance_euros_millicents == 0


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
def test_prepaid_overutilization_negative_balance(payment_status):
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=3 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=payment_status,
    )
    assert invoice.compute_costs_balance_euros_millicents == -3 * 1000 * 100


@pytest.mark.django_db
def test_prepaid_utilization_expired_zero_balance():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        compute_costs_utilized_euros_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=now().date() - timedelta(days=2),
    )
    assert invoice.compute_costs_balance_euros_millicents == 0


@pytest.mark.django_db
def test_prepaid_overutilization_expired_negative_balance():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=3 * 1000 * 100,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=now().date() - timedelta(days=2),  # Expired
    )
    assert invoice.compute_costs_balance_euros_millicents == -2 * 1000 * 100


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
def test_postpaid_no_utilization(
    prepaid_payment_status,
    postpaid_payment_status,
):
    challenge = ChallengeFactory()
    if prepaid_payment_status is not None:
        InvoiceFactory(
            challenge=challenge,
            compute_costs_euros=1,
            compute_costs_utilized_euros_millicents=0,
            payment_type=PaymentTypeChoices.PREPAID,
            payment_status=prepaid_payment_status,
        )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=2,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=postpaid_payment_status,
    )

    assert (
        postpaid_invoice.compute_costs_balance_euros_millicents
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
def test_postpaid_postpaid_status_interaction_zero_balance(
    prepaid_payment_status, postpaid_payment_status
):
    challenge = ChallengeFactory()
    if prepaid_payment_status is not None:
        InvoiceFactory(
            challenge=challenge,
            compute_costs_euros=1,
            compute_costs_utilized_euros_millicents=0,
            payment_type=PaymentTypeChoices.PREPAID,
            payment_status=prepaid_payment_status,
        )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=2,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=postpaid_payment_status,
    )

    assert postpaid_invoice.compute_costs_balance_euros_millicents == 0


@pytest.mark.django_db
def test_postpaid_with_expired_paid_prepaid():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=now().date() - timedelta(days=2),
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=2,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=PaymentStatusChoices.INITIALIZED,
    )

    assert (
        postpaid_invoice.compute_costs_balance_euros_millicents
        == 2 * 1000 * 100
    )


@pytest.mark.django_db
def test_postpaid_utilized():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        compute_costs_utilized_euros_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    assert (
        postpaid_invoice.compute_costs_balance_euros_millicents
        == 3 * 1000 * 100
    )


@pytest.mark.django_db
def test_postpaid_utilized_but_expired():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        compute_costs_utilized_euros_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=now().date() - timedelta(days=2),
        follow_up_on=now() - timedelta(days=3),
    )

    assert postpaid_invoice.compute_costs_balance_euros_millicents == 0


@pytest.mark.django_db
def test_postpaid_overutilized():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=3 * 1000 * 100,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    assert (
        postpaid_invoice.compute_costs_balance_euros_millicents
        == -2 * 1000 * 100
    )


@pytest.mark.django_db
def test_postpaid_overutilized_but_expired():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    postpaid_invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=3 * 1000 * 100,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=now().date() - timedelta(days=2),
        follow_up_on=now() - timedelta(days=3),
    )
    assert (
        postpaid_invoice.compute_costs_balance_euros_millicents
        == -2 * 1000 * 100
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
def test_complimentary_no_utilization_positive_balance(payment_status):
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=payment_status,
    )
    assert invoice.compute_costs_balance_euros_millicents == 1 * 1000 * 100


@pytest.mark.django_db
def test_complimentary_cancelled():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=PaymentStatusChoices.CANCELLED,
    )
    assert invoice.compute_costs_balance_euros_millicents == 0


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
def test_complimentary_utilized(payment_status):
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        compute_costs_utilized_euros_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=payment_status,
    )
    assert invoice.compute_costs_balance_euros_millicents == 3 * 1000 * 100


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
def test_complimentary_utilized_but_expired(payment_status):
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=4,
        compute_costs_utilized_euros_millicents=1 * 1000 * 100,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=payment_status,
        expires_on=now().date() - timedelta(days=2),
    )
    assert invoice.compute_costs_balance_euros_millicents == 0


@pytest.mark.django_db
def test_complimentary_overutilized_but_expired():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=3 * 1000 * 100,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        payment_status=PaymentStatusChoices.PAID,
        expires_on=now().date() - timedelta(days=2),
    )
    assert invoice.compute_costs_balance_euros_millicents == -2 * 1000 * 100


@pytest.mark.django_db
def test_multiple_challenges_do_not_mix_prepaid():
    challenge_with_prepaid = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge_with_prepaid,
        compute_costs_euros=2,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    challenge_without_prepaid = ChallengeFactory()
    postpaid_invoice = InvoiceFactory(
        challenge=challenge_without_prepaid,
        compute_costs_euros=1,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on=now() - timedelta(days=3),
    )
    assert postpaid_invoice.compute_costs_balance_euros_millicents == 0

    # Add prepaid
    InvoiceFactory(
        challenge=challenge_without_prepaid,
        compute_costs_euros=2,
        compute_costs_utilized_euros_millicents=0,
        payment_type=PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    postpaid_invoice = Invoice.objects.get(pk=postpaid_invoice.pk)
    assert (
        postpaid_invoice.compute_costs_balance_euros_millicents
        == 1 * 1000 * 100
    )
