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
def test_api_challenge_get(client):
    _, token = get_normal_user_with_token()

    n_challenges = 5
    challenges = [ChallengeFactory() for i in range(n_challenges)]

    url = reverse(f"api:challenge-list")
    response = client.get(
        url,
        HTTP_ACCEPT="text/html",
        HTTP_AUTHORIZATION="Token " + token
    )
    assert response.status_code == 200
    assert "Challenge List" in force_text(response.content)

    response = client.get(
        url,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token
    )
    assert response.status_code == 200
    j = json.loads(response.content)
    assert len(j) == n_challenges
    for i, c in enumerate(challenges):
        assert j[i]['short_name'] == challenges[i].short_name
        assert j[i]['creator'] == challenges[i].creator.pk

    url = reverse("api:challenge-detail", kwargs={"pk": challenges[0].pk})
    response = client.get(
        url,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token
    )
    assert response.status_code == 200
    j = json.loads(response.content)
    assert j["short_name"] == challenges[0].short_name


@pytest.mark.django_db
def test_api_challenge_post(client):
    user, token = get_normal_user_with_token()
    short_name = "test-challenge"

    url = reverse(f"api:challenge-list")
    response = client.post(
        url,
        {"short_name": short_name},
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token
    )
    assert response.status_code == 201
    j = json.loads(response.content)
    assert j["short_name"] == short_name
    assert j["creator"] == user.pk


@pytest.mark.django_db
def test_api_challenge_put(client):
    c = ChallengeFactory()
    token = Token.objects.create(user=c.creator).key
    updated_short_name = "updated-short-name"

    url = reverse(f"api:challenge-detail", kwargs={"pk": c.pk})
    response = client.put(
        url,
        {"short_name": updated_short_name},
        content_type="application/json",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token
    )
    assert response.status_code == 200
    j = json.loads(response.content)
    assert j["short_name"] == updated_short_name

    user2, token2 = get_normal_user_with_token()
    response = client.put(
        url,
        {"short_name": "this-goes-wrong"},
        content_type="application/json",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token2
    )
    assert response.status_code == 403
