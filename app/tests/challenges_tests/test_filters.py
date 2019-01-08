import pytest

from grandchallenge.subdomains.utils import reverse
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_challenge_list_is_filtered(client, TwoChallengeSets):
    c1 = TwoChallengeSets.ChallengeSet1.challenge.short_name
    c2 = TwoChallengeSets.ChallengeSet2.challenge.short_name
    tests = [
        ([], [c1, c2], TwoChallengeSets.ChallengeSet1.non_participant),
        ([c1], [c2], TwoChallengeSets.ChallengeSet1.participant),
        ([c1], [c2], TwoChallengeSets.ChallengeSet1.participant1),
        ([c1], [c2], TwoChallengeSets.ChallengeSet1.creator),
        ([c1], [c2], TwoChallengeSets.ChallengeSet1.admin),
        ([], [c1, c2], TwoChallengeSets.ChallengeSet2.non_participant),
        ([c2], [c1], TwoChallengeSets.ChallengeSet2.participant),
        ([c2], [c1], TwoChallengeSets.ChallengeSet2.participant1),
        ([c2], [c1], TwoChallengeSets.ChallengeSet2.creator),
        ([c2], [c1], TwoChallengeSets.ChallengeSet2.admin),
        ([c1, c2], [], TwoChallengeSets.admin12),
        ([c1, c2], [], TwoChallengeSets.participant12),
        ([c1, c2], [], TwoChallengeSets.admin1participant2),
    ]
    for test in tests:
        response = get_view_for_user(
            url=reverse("challenges:users-list"), client=client, user=test[2]
        )
        for short_name in test[0]:
            assert short_name in response.rendered_content
        for short_name in test[1]:
            assert short_name not in response.rendered_content
