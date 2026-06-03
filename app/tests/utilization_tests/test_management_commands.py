from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command

from grandchallenge.invoices.models import Invoice
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.factories import ChallengeFactory
from tests.invoices_tests.factories import InvoiceFactory


@pytest.mark.django_db
def test_no_challenges():
    call_command("route_challenge_utilizations_to_invoices")


@pytest.mark.django_db
def test_links_job_utilization_to_authorized_invoice():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    job = AlgorithmJobFactory()
    job.utilization.challenge = challenge
    job.utilization.compute_cost_euro_millicents = 1
    job.utilization.save()

    assert job.utilization.invoice is None

    call_command("route_challenge_utilizations_to_invoices")

    job.utilization.refresh_from_db()
    assert job.utilization.invoice == invoice

    invoice.refresh_from_db()
    assert invoice.compute_cost_euro_millicents == 1


@pytest.mark.django_db
def test_does_not_link_job_utilization_without_authorized_invoice():
    challenge = ChallengeFactory(short_name="TestChallenge")
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        payment_status=Invoice.PaymentStatusChoices.CANCELLED,
    )
    job = AlgorithmJobFactory()
    job.utilization.challenge = challenge
    job.utilization.compute_cost_euro_millicents = 1
    job.utilization.save()

    assert (
        not Invoice.objects.with_budget_authorization()
        .filter(is_budget_authorized=True)
        .exists()
    )

    out = StringIO()
    call_command("route_challenge_utilizations_to_invoices", stdout=out)

    job.utilization.refresh_from_db()
    assert job.utilization.invoice is None
    assert (
        "no authorized invoice found for 1 challenge: TestChallenge"
        in out.getvalue()
    )


@pytest.mark.django_db
def test_multiple_utilizations_linked_to_same_invoice():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    jobs = AlgorithmJobFactory.create_batch(3)
    for job in jobs:
        job.utilization.challenge = challenge
        job.utilization.compute_cost_euro_millicents = 1
        job.utilization.save()

    call_command("route_challenge_utilizations_to_invoices")

    for job in jobs:
        job.utilization.refresh_from_db()
        assert job.utilization.invoice == invoice


@pytest.mark.django_db
def test_budget_exhausted_rolls_over_to_next_invoice():
    # 1 euro = 100,000 millicents; invoice_1 has exactly that budget
    challenge = ChallengeFactory()
    invoice_1 = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    invoice_2 = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    job_1, job_2 = AlgorithmJobFactory.create_batch(2)
    job_1.utilization.challenge = challenge
    job_1.utilization.compute_cost_euro_millicents = 1 * 1000 * 100
    job_1.utilization.save()
    job_2.utilization.challenge = challenge
    job_2.utilization.compute_cost_euro_millicents = 1 * 1000 * 100
    job_2.utilization.save()

    call_command("route_challenge_utilizations_to_invoices")

    job_1.utilization.refresh_from_db()
    job_2.utilization.refresh_from_db()
    assert job_1.utilization.invoice == invoice_1
    assert job_2.utilization.invoice == invoice_2


@pytest.mark.django_db
def test_utilizations_for_different_challenges_link_to_their_own_invoice():
    challenge_a = ChallengeFactory()
    challenge_b = ChallengeFactory()
    invoice_a = InvoiceFactory(
        challenge=challenge_a,
        compute_costs_euros=100,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    invoice_b = InvoiceFactory(
        challenge=challenge_b,
        compute_costs_euros=100,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    job_a, job_b = AlgorithmJobFactory.create_batch(2)
    job_a.utilization.challenge = challenge_a
    job_a.utilization.compute_cost_euro_millicents = 1
    job_a.utilization.save()
    job_b.utilization.challenge = challenge_b
    job_b.utilization.compute_cost_euro_millicents = 2
    job_b.utilization.save()

    call_command("route_challenge_utilizations_to_invoices")

    job_a.utilization.refresh_from_db()
    job_b.utilization.refresh_from_db()
    assert job_a.utilization.invoice == invoice_a
    assert job_b.utilization.invoice == invoice_b


@pytest.mark.django_db
def test_already_linked_utilization_is_not_overwritten():
    challenge = ChallengeFactory()
    InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    invoice_2 = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    job = AlgorithmJobFactory()
    job.utilization.challenge = challenge
    job.utilization.compute_cost_euro_millicents = 1
    job.utilization.invoice = invoice_2
    job.utilization.save()

    call_command("route_challenge_utilizations_to_invoices")

    job.utilization.refresh_from_db()
    assert (
        job.utilization.invoice == invoice_2
    )  # not changed to earlier invoice


@pytest.mark.django_db
def test_non_challenge_utilization_is_skipped():
    # Utilizations not associated with a challenge are excluded from the queryset.
    job = AlgorithmJobFactory()
    assert job.utilization.challenge is None

    call_command("route_challenge_utilizations_to_invoices")

    job.utilization.refresh_from_db()
    assert job.utilization.invoice is None


@pytest.mark.django_db
def test_null_compute_cost_utilization_is_linked():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    job = AlgorithmJobFactory()
    job.utilization.challenge = challenge
    # compute_cost_euro_millicents intentionally left as None
    job.utilization.save()

    assert job.utilization.compute_cost_euro_millicents is None

    call_command("route_challenge_utilizations_to_invoices")

    job.utilization.refresh_from_db()
    invoice.refresh_from_db()
    assert job.utilization.invoice == invoice
    assert invoice.compute_cost_euro_millicents == 0


@pytest.mark.django_db
def test_overcharge_falls_on_final_invoice():
    challenge = ChallengeFactory()
    invoice = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=0,  # Note: zero budget, so any cost will be an overcharge
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    job = AlgorithmJobFactory()
    job.utilization.challenge = challenge
    job.utilization.compute_cost_euro_millicents = (
        5 * 1000 * 100  # 5× the budget
    )
    job.utilization.save()

    call_command("route_challenge_utilizations_to_invoices")

    job.utilization.refresh_from_db()
    assert job.utilization.invoice == invoice


@pytest.mark.django_db
def test_existing_invoice_spend_is_accounted_for_in_routing():
    challenge = ChallengeFactory()
    _ = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        compute_cost_euro_millicents=1 * 1000 * 100,  # already fully spent
    )
    invoice_2 = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=100,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )
    job = AlgorithmJobFactory()
    job.utilization.challenge = challenge
    job.utilization.compute_cost_euro_millicents = 2
    job.utilization.save()

    call_command("route_challenge_utilizations_to_invoices")

    job.utilization.refresh_from_db()
    assert (
        job.utilization.invoice == invoice_2
    )  # invoice_1 was already fully spent

    # The command should have updated the compute costs
    invoice_2.refresh_from_db()
    assert invoice_2.compute_cost_euro_millicents == 2


@pytest.mark.django_db
def test_expired_invoice_is_skipped_in_routing():
    challenge = ChallengeFactory()
    _ = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=date.today() - timedelta(days=1),  # expired yesterday
    )
    invoice_2 = InvoiceFactory(
        challenge=challenge,
        compute_costs_euros=1,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        expires_on=date.today() + timedelta(days=365),
    )
    job = AlgorithmJobFactory()
    job.utilization.challenge = challenge
    job.utilization.compute_cost_euro_millicents = 1
    job.utilization.save()

    call_command("route_challenge_utilizations_to_invoices")

    job.utilization.refresh_from_db()
    assert (
        job.utilization.invoice == invoice_2
    )  # invoice_1 had expired before creation
