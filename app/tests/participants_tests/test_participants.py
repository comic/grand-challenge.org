import pytest

from tests.utils import validate_admin_only_view, validate_logged_in_view


@pytest.mark.django_db
def test_registration_request_list(client, TwoChallengeSets):

    view = 'participants:registration-list'

    validate_admin_only_view(
        viewname=view,
        two_challenge_set=TwoChallengeSets,
        client=client,
    )

@pytest.mark.django_db
def test_registration_request_create(client, ChallengeSet):

    validate_logged_in_view(
        viewname='participants:registration-create',
        challenge_set=ChallengeSet,
        client=client,
    )

