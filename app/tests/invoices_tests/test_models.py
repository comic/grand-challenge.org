import datetime

import pytest
from django.db import IntegrityError, transaction
from factory import fuzzy

from grandchallenge.challenges.models import Challenge
from grandchallenge.invoices.models import (
    PaymentStatusChoices,
    PaymentTypeChoices,
)
from tests.evaluation_tests.factories import PhaseFactory, SubmissionFactory
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
def test_most_recent_submission_datetime_no_submissions():
    ChallengeFactory()

    challenge = (
        Challenge.objects.with_most_recent_submission_datetime().first()
    )
    assert challenge.most_recent_submission_datetime is None


@pytest.mark.django_db
def test_most_recent_submission_datetime_single_submission():
    submission = SubmissionFactory()

    challenge = (
        Challenge.objects.with_most_recent_submission_datetime().first()
    )
    assert challenge.most_recent_submission_datetime == submission.created


@pytest.mark.django_db
def test_most_recent_submission_datetime_multiple_submissions():
    challenge = ChallengeFactory()

    phase1 = PhaseFactory(challenge=challenge)
    SubmissionFactory(phase=phase1)
    phase2 = PhaseFactory(challenge=challenge)
    SubmissionFactory(phase=phase2)
    last_submission = SubmissionFactory(phase=phase2)

    challenge = (
        Challenge.objects.with_most_recent_submission_datetime().first()
    )
    assert challenge.most_recent_submission_datetime == last_submission.created


@pytest.mark.django_db
def test_payment_status_issued_requires_issued_on():
    invoice = InvoiceFactory()

    invoice.payment_status = invoice.PaymentStatusChoices.ISSUED
    with pytest.raises(IntegrityError) as e, transaction.atomic():
        invoice.save()
    assert (
        'violates check constraint "issued_on_date_required_for_issued_payment_status"'
    ) in str(e.value)

    invoice.issued_on = fuzzy.FuzzyDate(datetime.date(1970, 1, 1)).fuzz()
    invoice.save()

    invoice.paid_on = None
    invoice.payment_type = PaymentTypeChoices.COMPLIMENTARY
    invoice.save()


@pytest.mark.django_db
def test_payment_status_paid_requires_paid_on():
    invoice = InvoiceFactory()

    invoice.payment_status = invoice.PaymentStatusChoices.PAID
    with pytest.raises(IntegrityError) as e, transaction.atomic():
        invoice.save()
    assert (
        'violates check constraint "paid_on_date_required_for_paid_payment_status"'
    ) in str(e.value)

    invoice.paid_on = fuzzy.FuzzyDate(datetime.date(1970, 1, 1)).fuzz()
    invoice.save()

    invoice.paid_on = None
    invoice.payment_type = PaymentTypeChoices.COMPLIMENTARY
    invoice.save()


@pytest.mark.django_db
def test_payment_type_complimentary_requires_internal_comments():
    with pytest.raises(IntegrityError) as e, transaction.atomic():
        InvoiceFactory(
            payment_type=PaymentTypeChoices.COMPLIMENTARY,
            internal_comments="",
        )
    assert (
        'violates check constraint "comments_required_for_complimentary_payment_type"'
    ) in str(e.value)

    InvoiceFactory(
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
        internal_comments="some explanation",
    )
