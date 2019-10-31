import pytest

from tests.factories import RegistrationRequestFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_join_page_links(client, challenge_set):
    tests = [
        (challenge_set.non_participant, "Click here to join"),
        (challenge_set.participant, "You are already participating"),
    ]
    for test in tests:
        response = get_view_for_user(
            viewname="participants:registration-create",
            client=client,
            user=test[0],
            challenge=challenge_set.challenge,
        )
        assert test[1] in response.rendered_content
        rr = RegistrationRequestFactory(
            user=test[0], challenge=challenge_set.challenge
        )
        response = get_view_for_user(
            viewname="participants:registration-create",
            client=client,
            user=test[0],
            challenge=challenge_set.challenge,
        )
        assert rr.status_to_string() in response.rendered_content
