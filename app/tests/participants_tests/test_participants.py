import pytest

from tests.factories import RegistrationRequestFactory
from tests.utils import validate_admin_only_view, validate_logged_in_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'participants:registration-list',
        'participants:registration-update',
        'participants:list',
    ]
)
def test_registration_request_list(view, client, TwoChallengeSets):
    reverse_kwargs = {}
    if view in ('participants:registration-update',):
        rr = RegistrationRequestFactory(
            project=TwoChallengeSets.ChallengeSet1.challenge)
        reverse_kwargs.update({'pk': rr.pk})

    validate_admin_only_view(
        viewname=view,
        two_challenge_set=TwoChallengeSets,
        client=client,
        reverse_kwargs=reverse_kwargs,
    )


@pytest.mark.django_db
def test_registration_request_create(client, ChallengeSet):
    validate_logged_in_view(
        viewname='participants:registration-create',
        challenge_set=ChallengeSet,
        client=client,
    )
