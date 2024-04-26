import pytest

from tests.factories import ChallengeFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_challenge_is_suspended(client):
    c = ChallengeFactory(is_suspended=True)

    response = get_view_for_user(client=client, url=c.get_absolute_url())
    assert response.status_code == 302
    assert response.url == "https://testserver/challenge-suspended/"

    response = get_view_for_user(client=client, url=response.url)
    assert response.status_code == 200
    assert "Challenge Suspended" in response.content.decode()
