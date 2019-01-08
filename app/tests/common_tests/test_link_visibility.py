import pytest

from grandchallenge.subdomains.utils import reverse
from tests.utils import validate_admin_only_text_in_page


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "participants:registration-list",
        "participants:list",
        "admins:list",
        "uploads:list",
    ],
)
def test_admins_see_links(view, client, TwoChallengeSets):
    url = reverse(
        "challenge-homepage",
        kwargs={
            "challenge_short_name": TwoChallengeSets.ChallengeSet1.challenge.short_name
        },
    )
    expected = reverse(
        view,
        kwargs={
            "challenge_short_name": TwoChallengeSets.ChallengeSet1.challenge.short_name
        },
    )
    validate_admin_only_text_in_page(
        url=url,
        expected_text=f'"{str(expected)}"',
        two_challenge_set=TwoChallengeSets,
        client=client,
    )
