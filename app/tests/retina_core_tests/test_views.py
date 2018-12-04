import pytest
from rest_framework import status
from django.urls import reverse
from tests.retina_importers_tests.helpers import get_auth_token_header, get_user_with_token
from django.conf import settings

@pytest.mark.django_db
class TestTokenAuthentication:
    def test_no_auth(self, client):
        url = reverse("retina:home")
        response = client.get(url)
        assert response.status_code == status.HTTP_302_FOUND
        assert response.url == settings.LOGIN_URL + "?next=" + reverse("retina:home")

    def test_auth_normal(self, client):
        url = reverse("retina:home")
        user, token = get_user_with_token()
        client.force_login(user=user)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_auth_staff(self, client):
        url = reverse("retina:home")
        user, token = get_user_with_token()
        client.force_login(user=user)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    # TODO add retina user test
