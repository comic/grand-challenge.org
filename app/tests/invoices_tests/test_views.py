import pytest
from django.utils.timezone import now, timedelta

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
@pytest.mark.parametrize(
    "user_type, response_status_code",
    (
        ("user", 403),
        ("participant", 403),
        ("admin", 200),
    ),
)
def test_invoice_detail_view_permissions(
    client, user_type, response_status_code
):
    challenge = ChallengeFactory()

    user = UserFactory()
    if user_type == "participant":
        challenge.add_participant(user)
    elif user_type == "admin":
        challenge.add_admin(user)

    invoice = InvoiceFactory(challenge=challenge)

    response = get_view_for_user(
        viewname="invoices:detail",
        client=client,
        reverse_kwargs={"external_pk": invoice.external_pk},
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
def test_invoice_detail_hide_compute_when_expired(client):
    challenge = ChallengeFactory()

    user = UserFactory()
    challenge.add_admin(user)

    invoice = InvoiceFactory(challenge=challenge)

    response = get_view_for_user(
        viewname="invoices:detail",
        client=client,
        reverse_kwargs={"external_pk": invoice.external_pk},
        challenge=challenge,
        user=user,
    )
    assert response.status_code == 200

    assert "Compute Costs" in response.rendered_content

    invoice.expires_on = now().date() - timedelta(days=1)
    invoice.save()

    response = get_view_for_user(
        viewname="invoices:detail",
        client=client,
        reverse_kwargs={"external_pk": invoice.external_pk},
        challenge=challenge,
        user=user,
    )
    assert response.status_code == 200

    assert "Compute Costs" not in response.rendered_content
