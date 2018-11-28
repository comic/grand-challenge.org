import pytest
import json
from django.urls import reverse
from django.utils.encoding import force_text
from tests.factories import UserFactory, ChallengeFactory
from rest_framework.authtoken.models import Token


def get_normal_user_with_token():
    user = UserFactory()
    token = Token.objects.create(user=user)

    return user, token.key


def get_staff_user_with_token():
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key


@pytest.mark.django_db
def test_api_challenge(client):
    _, token = get_normal_user_with_token()

    n_challenges = 2
    for i in range(n_challenges):
        _ = ChallengeFactory()

    url = reverse(f"api:challenge-list")
    response = client.get(
        url, HTTP_ACCEPT="text/html", HTTP_AUTHORIZATION="Token " + token
    )
    assert response.status_code == 200
    assert "Challenge List" in force_text(response.content)

    response = client.get(
        url, HTTP_ACCEPT="application/json", HTTP_AUTHORIZATION="Token " + token
    )
    assert response.status_code == 200
    j = json.loads(response.content)
    assert len(j) == n_challenges