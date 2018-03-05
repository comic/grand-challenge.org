import pytest

from tests.utils import validate_admin_only_view


@pytest.mark.django_db
def test_registration_request_list(client, TwoChallengeSets):

    view = 'participants:registration-list'

    validate_admin_only_view(
        viewname=view,
        two_challenge_set=TwoChallengeSets,
        client=client,
    )
