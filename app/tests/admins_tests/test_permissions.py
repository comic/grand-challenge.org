import pytest

from tests.utils import validate_admin_only_view


@pytest.mark.django_db
@pytest.mark.parametrize("view", ["admins:list", "admins:update"])
def test_admins_list(view, client, two_challenge_sets):
    validate_admin_only_view(
        viewname=view, two_challenge_set=two_challenge_sets, client=client
    )
