import pytest

from grandchallenge.subdomains.utils import reverse
from tests.factories import RegistrationRequestFactory
from tests.utils import (
    get_view_for_user,
    validate_admin_only_view,
    validate_logged_in_view,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "participants:registration-list",
        "participants:registration-update",
        "participants:list",
    ],
)
def test_registration_request_list(view, client, two_challenge_sets):
    reverse_kwargs = {}
    if view in ("participants:registration-update",):
        rr = RegistrationRequestFactory(
            challenge=two_challenge_sets.challenge_set_1.challenge
        )
        reverse_kwargs.update({"pk": rr.pk})
    validate_admin_only_view(
        viewname=view,
        two_challenge_set=two_challenge_sets,
        client=client,
        reverse_kwargs=reverse_kwargs,
    )


@pytest.mark.django_db
def test_registration_request_create_get(client, challenge_set):
    validate_logged_in_view(
        viewname="participants:registration-create",
        challenge_set=challenge_set,
        client=client,
    )
    # Make sure the link to register is in the challenge page
    url = reverse(
        "pages:home",
        kwargs={"challenge_short_name": challenge_set.challenge.short_name},
    )
    response = get_view_for_user(url=url, client=client)
    expected_link = reverse(
        "participants:registration-create",
        kwargs={"challenge_short_name": challenge_set.challenge.short_name},
    )
    assert f'"{expected_link}"' in str(response.content)
