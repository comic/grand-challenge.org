import pytest
from rest_framework import status
from django.urls import reverse
from tests.retina_importers_tests.helpers import get_auth_token_header, get_user_with_token
from django.conf import settings

@pytest.mark.django_db
class TestTokenAuthentication:
    def test_no_auth(self, client):
        url = reverse("retina:home")
        response = client.get(url, follow=True)

        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert (
            settings.LOGIN_URL + "?next=" + reverse("retina:home")
            == response.redirect_chain[0][0]
        )
        assert status.HTTP_200_OK == response.status_code

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
