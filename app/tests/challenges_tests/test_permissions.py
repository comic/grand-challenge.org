import pytest

from core.urlresolvers import reverse
from tests.utils import validate_logged_in_view, validate_admin_only_view


@pytest.mark.django_db
@pytest.mark.parametrize("view", ['challenges:create', 'challenges:list'])
def test_challenge_logged_in_permissions(view, client, ChallengeSet):
    validate_logged_in_view(
        url=reverse(view), challenge_set=ChallengeSet, client=client
    )


@pytest.mark.django_db
def test_challenge_update_permissions(client, TwoChallengeSets):
    validate_admin_only_view(
        two_challenge_set=TwoChallengeSets,
        viewname='challenges:update',
        client=client,
    )
