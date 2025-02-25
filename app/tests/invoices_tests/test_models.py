import pytest

from grandchallenge.challenges.models import Challenge
from grandchallenge.invoices.models import PaymentStatusChoices
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
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
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
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert (
        challenge.approved_compute_costs_euro_millicents
        == expected_budget * 1000 * 100
    )


@pytest.mark.django_db
def test_approved_compute_costs_budget_preapproved_no_paid_invoices():
    InvoiceFactory(
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.INITIALIZED,
        budget_preapproved=True,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 0


@pytest.mark.django_db
def test_approved_compute_costs_budget_preapproved_only_complimentary_invoice():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.INITIALIZED,
        budget_preapproved=True,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 1 * 1000 * 100


@pytest.mark.django_db
def test_approved_compute_costs_budget_preapproved_with_paid_invoice():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.INITIALIZED,
        budget_preapproved=True,
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
def test_approved_compute_costs_budget_preapproved_and_complimentary():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
        budget_preapproved=True,
    )
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
    )

    challenge = Challenge.objects.with_available_compute().first()
    assert challenge.approved_compute_costs_euro_millicents == 2 * 1000 * 100


@pytest.mark.django_db
def test_approved_compute_costs_budget_preapproved_and_paid():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
        budget_preapproved=True,
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
