import pytest

from grandchallenge.challenges.models import Challenge
from grandchallenge.invoices.models import PaymentStatusChoices
from tests.evaluation_tests.factories import PhaseFactory, SubmissionFactory
from tests.factories import ChallengeFactory
from tests.invoices_tests.factories import InvoiceFactory


@pytest.mark.flaky(reruns=3)
@pytest.mark.django_db
def test_approved_compute_costs_euro_millicents():
    c1, c2, c3, c4 = ChallengeFactory.create_batch(4)

    InvoiceFactory(
        challenge=c1,
        support_costs_euros=0,
        compute_costs_euros=1,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )

    InvoiceFactory(
        challenge=c2,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
    )
    InvoiceFactory(
        challenge=c2,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
    )

    InvoiceFactory(
        challenge=c3,
        support_costs_euros=50,
        compute_costs_euros=0,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=c3,
        support_costs_euros=50,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.ISSUED,
    )
    InvoiceFactory(
        challenge=c3,
        support_costs_euros=50,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.INITIALIZED,
    )
    InvoiceFactory(
        challenge=c3,
        support_costs_euros=50,
        compute_costs_euros=30,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    InvoiceFactory(
        challenge=c3,
        support_costs_euros=50,
        compute_costs_euros=30,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.ISSUED,
    )
    InvoiceFactory(
        challenge=c3,
        support_costs_euros=50,
        compute_costs_euros=0,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
    )

    p2a = PhaseFactory(challenge=c2)
    SubmissionFactory(phase=p2a)
    p2b = PhaseFactory(challenge=c2)
    SubmissionFactory(phase=p2b)
    s2 = SubmissionFactory(phase=p2b)

    p4 = PhaseFactory(challenge=c4)
    s4 = SubmissionFactory(phase=p4)

    for challenge, expected_budget, expected_datetime in zip(
        Challenge.objects.filter(pk__in=[c1.pk, c2.pk, c3.pk, c4.pk])
        .order_by("short_name")
        .with_available_compute()
        .with_most_recent_submission_datetime(),
        [1, 20, 30, 0],
        [None, s2.created, None, s4.created],
        strict=True,
    ):
        assert (
            challenge.approved_compute_costs_euro_millicents
            == expected_budget * 1000 * 100
        )
        assert challenge.most_recent_submission_datetime == expected_datetime
