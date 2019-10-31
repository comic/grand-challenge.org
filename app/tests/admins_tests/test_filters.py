import pytest

from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_admins_list_is_filtered(client, two_challenge_sets):
    response = get_view_for_user(
        viewname="admins:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.admin12,
    )
    tests = [
        (False, two_challenge_sets.challenge_set_1.non_participant),
        (False, two_challenge_sets.challenge_set_1.participant),
        (False, two_challenge_sets.challenge_set_1.participant1),
        (True, two_challenge_sets.challenge_set_1.creator),
        (True, two_challenge_sets.challenge_set_1.admin),
        (False, two_challenge_sets.challenge_set_2.non_participant),
        (False, two_challenge_sets.challenge_set_2.participant),
        (False, two_challenge_sets.challenge_set_2.participant1),
        (False, two_challenge_sets.challenge_set_2.creator),
        (False, two_challenge_sets.challenge_set_2.admin),
        (True, two_challenge_sets.admin12),
        (False, two_challenge_sets.participant12),
        (True, two_challenge_sets.admin1participant2),
    ]
    for test in tests:
        assert (test[1].username in response.rendered_content) == test[0]
    assert "Admins for " in response.rendered_content
