import pytest

from tests.factories import ChallengeFactory, UserFactory
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
        viewname="challenge-invoice-list",
        client=client,
        challenge=challenge,
        user=user,
    )
    assert response.status_code == response_status_code
