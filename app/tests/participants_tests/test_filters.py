import pytest

from tests.factories import RegistrationRequestFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_participants_list_is_filtered(client, two_challenge_sets):
    response = get_view_for_user(
        viewname="participants:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.admin12,
    )
    tests = [
        (False, two_challenge_sets.challenge_set_1.non_participant),
        (True, two_challenge_sets.challenge_set_1.participant),
        (True, two_challenge_sets.challenge_set_1.participant1),
        (False, two_challenge_sets.challenge_set_1.creator),
        (False, two_challenge_sets.challenge_set_1.admin),
        (False, two_challenge_sets.challenge_set_2.non_participant),
        (False, two_challenge_sets.challenge_set_2.participant),
        (False, two_challenge_sets.challenge_set_2.participant1),
        (False, two_challenge_sets.challenge_set_2.creator),
        (False, two_challenge_sets.challenge_set_2.admin),
        # admin12 is in the response as they're loading the page
        (True, two_challenge_sets.admin12),
        (True, two_challenge_sets.participant12),
        (False, two_challenge_sets.admin1participant2),
    ]
    for test in tests:
        assert (test[1].username in response.rendered_content) == test[0]
    assert "Participants for " in response.rendered_content


@pytest.mark.django_db
def test_registration_list_is_filtered(client, two_challenge_sets):
    r1 = RegistrationRequestFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge
    )
    r2 = RegistrationRequestFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge
    )
    response = get_view_for_user(
        viewname="participants:registration-list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.admin12,
    )
    assert r1.user.username in response.rendered_content
    assert r2.user.username not in response.rendered_content
