import pytest

from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_admins_list_is_filtered(client, TwoChallengeSets):
    response = get_view_for_user(
        viewname='admins:list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.admin12,
    )
    tests = [
        (False, TwoChallengeSets.ChallengeSet1.non_participant),
        (False, TwoChallengeSets.ChallengeSet1.participant),
        (False, TwoChallengeSets.ChallengeSet1.participant1),
        (True, TwoChallengeSets.ChallengeSet1.creator),
        (True, TwoChallengeSets.ChallengeSet1.admin),
        (False, TwoChallengeSets.ChallengeSet2.non_participant),
        (False, TwoChallengeSets.ChallengeSet2.participant),
        (False, TwoChallengeSets.ChallengeSet2.participant1),
        (False, TwoChallengeSets.ChallengeSet2.creator),
        (False, TwoChallengeSets.ChallengeSet2.admin),
        (True, TwoChallengeSets.admin12),
        (False, TwoChallengeSets.participant12),
        (True, TwoChallengeSets.admin1participant2),
    ]
    for test in tests:
        assert (test[1].username in response.rendered_content) == test[0]
    assert 'Admins for ' in response.rendered_content
