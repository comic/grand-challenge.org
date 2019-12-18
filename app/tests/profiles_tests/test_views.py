import pytest
from django.conf import settings
from rest_framework import status

from grandchallenge.subdomains.utils import reverse
from tests.factories import PolicyFactory, UserFactory


@pytest.mark.django_db
class TestLoginRedirect:
    def test_default_redirect(self, client):
        url = reverse("login_redirect")
        response = client.get(url, follow=True)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.redirect_chain[0][0] == reverse("home")
        assert response.status_code == status.HTTP_200_OK

    def test_normal_redirect(self, client):
        redirect_to = "/challenges/"
        url = reverse("login_redirect") + f"?next={redirect_to}"
        response = client.get(url, follow=True)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.redirect_chain[0][0] == redirect_to
        assert response.status_code == status.HTTP_200_OK

    def test_redirect_to_logout_url(self, client):
        url = reverse("login_redirect") + f"?next={settings.LOGOUT_URL}"
        response = client.get(url, follow=True)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.redirect_chain[0][0] == reverse("home")
        assert response.status_code == status.HTTP_200_OK

    def test_redirect_to_logout_url_absolute(self, client):
        url = (
            reverse("login_redirect")
            + f"?next={reverse('home')}{settings.LOGOUT_URL[1:]}"
        )
        response = client.get(url, follow=True)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.redirect_chain[0][0] == reverse("home")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSignInRedirect:
    def get_redirect_response(self, client, next=None):
        password = "password"
        self.user = UserFactory()
        self.user.set_password(password)
        self.user.save()
        url = reverse("userena_signin")
        if next:
            url += f"?next={next}"

        return client.post(
            url,
            data={"identification": self.user.username, "password": password},
            follow=True,
        )

    def test_default_redirect(self, client):
        response = self.get_redirect_response(client)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.redirect_chain[0][0] == reverse("profile_redirect")
        assert response.status_code == status.HTTP_200_OK

    def test_redirect(self, client):
        expected_url = "/challenges/"
        response = self.get_redirect_response(client, expected_url)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.status_code == status.HTTP_200_OK
        assert response.redirect_chain[0][0] == expected_url

    def test_no_logout_redirect(self, client):
        response = self.get_redirect_response(client, settings.LOGOUT_URL)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.redirect_chain[0][0] == reverse("profile_redirect")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUrlEncodedUsername:
    def test_special_username(self, client):
        user = UserFactory(username="tést")
        url = reverse("profile_redirect")
        client.force_login(user)
        response = client.get(url, follow=True)
        assert response.status_code == status.HTTP_200_OK
        assert "t%C3%A9st" in response.redirect_chain[0][0]


@pytest.mark.django_db
def test_terms_form_fields(client):
    p = PolicyFactory(title="terms", body="blah")
    response = client.get(reverse("profile_signup"))
    assert response.status_code == 200
    assert p.get_absolute_url() in response.rendered_content
    response = client.get(reverse("pre-social"))
    assert response.status_code == 200
    assert p.get_absolute_url() in response.rendered_content
