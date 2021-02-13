import pytest
from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.test import force_authenticate

from grandchallenge.profiles.views import UserProfileViewSet
from grandchallenge.subdomains.utils import reverse
from tests.factories import PolicyFactory, UserFactory


@pytest.mark.django_db
class TestSignInRedirect:
    def get_redirect_response(self, client, next=None):
        password = "password"

        self.user = UserFactory()
        self.user.set_password(password)
        self.user.save()

        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True
        )

        url = reverse("account_login")
        if next:
            url += f"?next={next}"

        return client.post(
            url,
            data={"login": self.user.username, "password": password},
            follow=True,
        )

    def test_default_redirect(self, client):
        response = self.get_redirect_response(client)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert reverse("profile-detail-redirect").endswith(
            response.redirect_chain[0][0]
        )
        assert response.status_code == status.HTTP_200_OK

    def test_redirect(self, client):
        expected_url = "/challenges/"
        response = self.get_redirect_response(client, expected_url)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.status_code == status.HTTP_200_OK
        assert response.redirect_chain[0][0] == expected_url


@pytest.mark.django_db
class TestUrlEncodedUsername:
    def test_special_username(self, client):
        user = UserFactory(username="tést")
        url = reverse("profile-detail-redirect")
        client.force_login(user)
        response = client.get(url, follow=True)
        assert response.status_code == status.HTTP_200_OK
        assert "t%C3%A9st" in response.redirect_chain[0][0]


@pytest.mark.django_db
def test_terms_form_fields(client):
    p = PolicyFactory(title="terms", body="blah")
    response = client.get(reverse("account_signup"))
    assert response.status_code == 200
    assert p.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
class TestProfileViewSets:
    def test_profile_self_not_logged_in(self, rf):
        UserFactory()
        url = reverse("api:profiles-user-self")
        request = rf.get(url)
        response = UserProfileViewSet.as_view(actions={"get": "self"})(request)
        assert response.status_code == 401

    def test_profile_self(self, rf):
        user = UserFactory()
        url = reverse("api:profiles-user-self")
        request = rf.get(url)
        force_authenticate(request, user=user)
        response = UserProfileViewSet.as_view(actions={"get": "self"})(request)
        assert response.status_code == 200
        assert response.data["user"] == {
            "username": user.username
        }  # no user id
        for field in (
            "mugshot",
            "institution",
            "department",
            "location",
            "website",
        ):
            assert field in response.data
        assert "country" not in response.data
