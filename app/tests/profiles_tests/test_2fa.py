import pytest
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.tests import OAuth2TestsMixin
from allauth.tests import MockedResponse
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from pytest_django.asserts import assertRedirects

from config.settings import LOGIN_REDIRECT_URL
from grandchallenge.profiles.providers.gmail.provider import GmailProvider
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_2fa_required_for_staff(client):
    admin = UserFactory(is_staff=True)
    user = UserFactory()

    response = get_view_for_user(
        viewname="account_login",
        client=client,
        method=client.post,
        data={"login": user.username, "password": user.password},
        user=user,
    )
    assertRedirects(
        response, LOGIN_REDIRECT_URL, fetch_redirect_response=False
    )

    response = get_view_for_user(
        viewname="account_login",
        client=client,
        method=client.post,
        data={"login": admin.username, "password": admin.password},
        user=admin,
    )
    assertRedirects(
        response, "/accounts/two_factor/setup", fetch_redirect_response=False
    )


class SocialLoginTests(OAuth2TestsMixin, TestCase):
    provider_id = GmailProvider.id

    def get_mocked_response(
        self,
        family_name="Doe",
        given_name="Jane",
        name="Jane Doe",
        email="jane.doe@example.com",
        verified_email=True,
    ):
        return MockedResponse(
            200,
            """
                {"family_name": "%s", "name": "%s",
                "picture": "https://lh5.googleusercontent.com/photo.jpg",
                "locale": "nl", "gender": "female",
                "email": "%s",
                "link": "https://plus.google.com/108204268033311374519",
                "given_name": "%s", "id": "108204268033311374519",
                "verified_email": %s }
            """
            % (
                family_name,
                name,
                email,
                given_name,
                (repr(verified_email).lower()),
            ),
        )

    @override_settings(SOCIALACCOUNT_AUTO_SIGNUP=True)
    @pytest.mark.django_db
    def test_2fa_for_social_login(self):
        # login with test user
        resp = self.login(resp_mock=self.get_mocked_response())
        # check that a social account has been created
        assert SocialAccount.objects.count() == 1
        assertRedirects(resp, "/users/profile/", fetch_redirect_response=False)

        # make this user staff user
        user = get_user_model().objects.last()
        assert user.email == "jane.doe@example.com"
        user.is_staff = True
        user.save()

        # log user out
        self.client.logout()

        # log back in, check that redirect is now to 2fa setup page
        resp = self.login(resp_mock=self.get_mocked_response())
        assert "two_factor/setup" in resp.url

        # enable 2fa for the user (mimicks the 2fa setup)
        user.totpdevice_set.create()

        # log user out
        self.client.logout()

        # sign in again, check that redirect is now to 2fa authenticate page
        resp = self.login(resp_mock=self.get_mocked_response())
        assert "two-factor-authenticate" in resp.url
