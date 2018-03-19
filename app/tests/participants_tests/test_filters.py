import pytest

from tests.factories import RegistrationRequestFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_participants_list_is_filtered(client, TwoChallengeSets):
    response = get_view_for_user(
        viewname='participants:list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.admin12,
    )
    tests = [
        (False, TwoChallengeSets.ChallengeSet1.non_participant),
        (True, TwoChallengeSets.ChallengeSet1.participant),
        (True, TwoChallengeSets.ChallengeSet1.participant1),
        (False, TwoChallengeSets.ChallengeSet1.creator),
        (False, TwoChallengeSets.ChallengeSet1.admin),
        (False, TwoChallengeSets.ChallengeSet2.non_participant),
        (False, TwoChallengeSets.ChallengeSet2.participant),
        (False, TwoChallengeSets.ChallengeSet2.participant1),
        (False, TwoChallengeSets.ChallengeSet2.creator),
        (False, TwoChallengeSets.ChallengeSet2.admin),
        # admin12 is in the response as they're loading the page
        (True, TwoChallengeSets.admin12),
        (True, TwoChallengeSets.participant12),
        (False, TwoChallengeSets.admin1participant2),
    ]
    for test in tests:
        assert (test[1].username in response.rendered_content) == test[0]
    assert 'Participants for ' in response.rendered_content


@pytest.mark.django_db
def test_registration_list_is_filtered(client, TwoChallengeSets):
    r1 = RegistrationRequestFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge
    )
    r2 = RegistrationRequestFactory(
        challenge=TwoChallengeSets.ChallengeSet2.challenge
    )
    response = get_view_for_user(
        viewname='participants:registration-list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.admin12,
    )
    assert r1.user.username in response.rendered_content
    assert r2.user.username not in response.rendered_content
