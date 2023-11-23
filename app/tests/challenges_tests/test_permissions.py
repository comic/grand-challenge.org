import pytest

from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import Verification
from tests.factories import UserFactory
from tests.utils import (
    get_view_for_user,
    validate_admin_only_view,
    validate_logged_in_view,
)


@pytest.mark.django_db
@pytest.mark.parametrize("view", ["challenges:users-list"])
def test_challenge_logged_in_permissions(view, client, challenge_set):
    validate_logged_in_view(
        url=reverse(view), challenge_set=challenge_set, client=client
    )


@pytest.mark.django_db
def test_challenge_update_permissions(client, two_challenge_sets):
    validate_admin_only_view(
        two_challenge_set=two_challenge_sets,
        viewname="challenge-update",
        client=client,
    )


@pytest.mark.django_db
def test_request_challenge_only_when_verified(client):
    user = UserFactory()
    assert not Verification.objects.filter(user=user)
    response = get_view_for_user(
        client=client, viewname="challenges:requests-create", user=user
    )
    assert response.status_code == 403
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-cost-calculation",
        user=user,
    )
    assert response.status_code == 403
    Verification.objects.create(user=user, is_verified=True)
    response = get_view_for_user(
        client=client, viewname="challenges:requests-create", user=user
    )
    assert response.status_code == 200
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-cost-calculation",
        user=user,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_view_and_update_challenge_request(
    client, challenge_reviewer, challenge_request
):
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-detail",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
    )
    assert response.status_code == 200
    assert "Edit budget fields" not in str(response.content)

    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-status-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-budget-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
    )
    assert response.status_code == 403

    # reviewer can view and update
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-detail",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
    )
    assert response.status_code == 200
    assert "Edit budget fields" in str(response.content)

    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-status-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
    )
    assert response.status_code == 200
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-budget-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
    )
    assert response.status_code == 200
