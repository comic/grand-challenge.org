from datetime import timedelta

import pytest
from django.conf import settings
from django.utils.timezone import now
from pytest_django.asserts import assertInHTML

from grandchallenge.invoices.models import Invoice
from tests.factories import ChallengeFactory, UserFactory
from tests.invoices_tests.factories import InvoiceFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type, response_status_code",
    (
        ("user", 403),
        ("participant", 403),
        ("admin", 200),
    ),
)
def test_invoice_list_view_permissions(
    client, user_type, response_status_code
):
    challenge = ChallengeFactory()

    user = UserFactory()
    if user_type == "participant":
        challenge.add_participant(user)
    elif user_type == "admin":
        challenge.add_admin(user)

    response = get_view_for_user(
        viewname="invoices:list",
        client=client,
        challenge=challenge,
        user=user,
    )
    assert response.status_code == response_status_code


@pytest.mark.django_db
def test_invoice_list_view_num_invoices_shown(client):
    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    for num_invoices in range(10):
        if num_invoices:
            InvoiceFactory(
                challenge=challenge,
                support_costs_euros=0,
                compute_costs_euros=10,
                storage_costs_euros=0,
            )

        response = get_view_for_user(
            viewname="invoices:list",
            client=client,
            challenge=challenge,
            user=challenge_admin,
        )
        assert response.status_code == 200
        assert len(response.context_data["object_list"]) == num_invoices


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invoice_kwargs, badge_and_status",
    (
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
            ),
            '<td><span class="badge badge-info">Initialized</span></td>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.REQUESTED,
            ),
            '<td><span class="badge badge-info">Initialized</span></td>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.ISSUED,
                issued_on=now() - settings.CHALLENGE_INVOICE_OVERDUE_CUTOFF,
            ),
            '<td><span class="badge badge-warning">Due</span></td>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.ISSUED,
                issued_on=now()
                - settings.CHALLENGE_INVOICE_OVERDUE_CUTOFF
                - timedelta(days=1),
            ),
            '<td><span class="badge badge-danger">Overdue</span></td>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.PAID,
            ),
            '<td><span class="badge badge-success">Paid</span></td>',
        ),
        (
            dict(
                payment_status=Invoice.PaymentStatusChoices.CANCELLED,
            ),
            '<td><span class="badge badge-dark">Cancelled</span></td>',
        ),
    ),
)
def test_invoice_list_view_content(client, invoice_kwargs, badge_and_status):
    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        **invoice_kwargs,
    )

    response = get_view_for_user(
        viewname="invoices:list",
        client=client,
        challenge=challenge,
        user=challenge_admin,
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 1
    assertInHTML(badge_and_status, response.rendered_content)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payment_status",
    Invoice.PaymentStatusChoices.values,
)
def test_invoice_list_view_content_complimentary_no_payment_status(
    client, payment_status
):
    challenge = ChallengeFactory()
    challenge_admin = challenge.creator

    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_type=Invoice.PaymentTypeChoices.COMPLIMENTARY,
        payment_status=payment_status,
    )

    response = get_view_for_user(
        viewname="invoices:list",
        client=client,
        challenge=challenge,
        user=challenge_admin,
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 1
    assertInHTML(
        "<td>Complimentary</td><td>-</td>",
        response.rendered_content,
    )
