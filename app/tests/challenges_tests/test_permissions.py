import pytest

from grandchallenge.subdomains.utils import reverse
from tests.factories import ExternalChallengeFactory
from tests.utils import (
    validate_admin_only_view,
    validate_logged_in_view,
    validate_staff_only_view,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view", ["challenges:create", "challenges:users-list"]
)
def test_challenge_logged_in_permissions(view, client, challenge_set):
    validate_logged_in_view(
        url=reverse(view), challenge_set=challenge_set, client=client
    )


@pytest.mark.django_db
def test_challenge_update_permissions(client, two_challenge_sets):
    validate_admin_only_view(
        two_challenge_set=two_challenge_sets, viewname="update", client=client
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "challenges:external-list",
        "challenges:external-create",
        "challenges:external-update",
        "challenges:external-delete",
    ],
)
def test_external_challenges_staff_views(client, view):
    if view in ["challenges:external-update", "challenges:external-delete"]:
        reverse_kwargs = {"short_name": ExternalChallengeFactory().short_name}
    else:
        reverse_kwargs = {}

    validate_staff_only_view(
        client=client, viewname=view, reverse_kwargs=reverse_kwargs
    )
