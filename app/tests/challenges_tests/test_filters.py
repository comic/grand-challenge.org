import pytest

from grandchallenge.subdomains.utils import reverse
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_challenge_list_is_filtered(client, two_challenge_sets):
    c1 = two_challenge_sets.challenge_set_1.challenge.short_name
    c2 = two_challenge_sets.challenge_set_2.challenge.short_name
    tests = [
        ([], [c1, c2], two_challenge_sets.challenge_set_1.non_participant),
        ([c1], [c2], two_challenge_sets.challenge_set_1.participant),
        ([c1], [c2], two_challenge_sets.challenge_set_1.participant1),
        ([c1], [c2], two_challenge_sets.challenge_set_1.creator),
        ([c1], [c2], two_challenge_sets.challenge_set_1.admin),
        ([], [c1, c2], two_challenge_sets.challenge_set_2.non_participant),
        ([c2], [c1], two_challenge_sets.challenge_set_2.participant),
        ([c2], [c1], two_challenge_sets.challenge_set_2.participant1),
        ([c2], [c1], two_challenge_sets.challenge_set_2.creator),
        ([c2], [c1], two_challenge_sets.challenge_set_2.admin),
        ([c1, c2], [], two_challenge_sets.admin12),
        ([c1, c2], [], two_challenge_sets.participant12),
        ([c1, c2], [], two_challenge_sets.admin1participant2),
    ]
    for test in tests:
        response = get_view_for_user(
            url=reverse("challenges:users-list"), client=client, user=test[2]
        )
        for short_name in test[0]:
            assert short_name in response.rendered_content
        for short_name in test[1]:
            assert short_name not in response.rendered_content
