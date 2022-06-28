from base64 import b32encode

import pytest
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.tests import OAuth2TestsMixin
from allauth.tests import MockedResponse
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django_otp.plugins.otp_static.models import StaticToken
from pytest_django.asserts import assertRedirects

from config.settings import LOGIN_REDIRECT_URL
from grandchallenge.profiles.providers.gmail.provider import GmailProvider
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from tests.conftest import get_token_from_totp_device
from tests.factories import (
    SUPER_SECURE_TEST_PASSWORD,
    ChallengeFactory,
    UserFactory,
)
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

        token = get_token_from_totp_device(user.totpdevice_set.get())
        resp = self.client.post(resp.url, {"otp_token": token})
        resp = self.client.post(resp.url)
        assert (
            reverse("profile-detail", kwargs={"username": user.username})
            in resp.url
        )


@override_settings(ACCOUNT_EMAIL_VERIFICATION=None)
@pytest.mark.django_db
def test_2fa_reset_flow(client):
    user = UserFactory()
    user.totpdevice_set.create()

    response = client.post(
        reverse_lazy("account_login"),
        {"login": user.username, "password": SUPER_SECURE_TEST_PASSWORD},
    )
    assert "/accounts/two-factor-authenticate" in response.url

    # The user ID should be in the session.
    assert client.session.get("allauth_2fa_user_id")

    # Navigate to a different page.
    client.get(reverse_lazy("algorithms:list"))

    # The middleware should reset the login flow.
    assert not client.session.get("allauth_2fa_user_id")

    # Trying to continue with two-factor without logging in again will
    # redirect to login.
    resp = client.get(reverse_lazy("two-factor-authenticate"))

    assert "/accounts/login/" in resp.url

    # navigate to a subdomain page
    client.post(
        reverse_lazy("account_login"),
        {"login": user.username, "password": SUPER_SECURE_TEST_PASSWORD},
    )
    assert client.session.get("allauth_2fa_user_id")
    target_url = reverse_lazy(
        "pages:home",
        kwargs={"challenge_short_name": ChallengeFactory().short_name},
    )
    client.get(target_url)
    assert not client.session.get("allauth_2fa_user_id")
    resp = client.get(reverse_lazy("two-factor-authenticate"))
    assert "/accounts/login/" == resp.url


@override_settings(ACCOUNT_EMAIL_VERIFICATION=None)
@pytest.mark.django_db
def test_2fa_removal(client):
    user = UserFactory()
    # enable 2fa
    totp_device = user.totpdevice_set.create()

    # generate some backup tokens
    static_device = user.staticdevice_set.create(name="backup")
    static_device.token_set.create(token=StaticToken.random_token())
    assert static_device.token_set.count() == 1

    # Navigate to 2FA removal view
    response = get_view_for_user(
        viewname="two-factor-remove",
        client=client,
        user=user,
    )

    # check that token is required
    assert 'required id="id_otp_token"' in response.rendered_content
    # submitting without a token does not work
    response = get_view_for_user(
        viewname="two-factor-remove",
        client=client,
        method=client.post,
        user=user,
    )
    assert "Please enter your OTP token." in str(
        response.context["form"].errors
    )

    # when correct token is entered, the totp device and any backup tokens are deleted
    token = get_token_from_totp_device(totp_device)
    _ = get_view_for_user(
        viewname="two-factor-remove",
        client=client,
        method=client.post,
        data={"otp_token": token},
        user=user,
    )
    user.refresh_from_db()
    assert not user.totpdevice_set.exists()
    assert static_device.token_set.count() == 0


@override_settings(ACCOUNT_EMAIL_VERIFICATION=None)
@pytest.mark.django_db
def test_2fa_setup(client):
    user = UserFactory()
    response = get_view_for_user(
        viewname="two-factor-setup",
        client=client,
        user=user,
    )

    # assert the text code is in the template
    secret_code = b32encode(user.totpdevice_set.get().bin_key).decode("utf-8")
    assert secret_code in response.rendered_content

    # filling in wrong token return error
    response = get_view_for_user(
        viewname="two-factor-setup",
        client=client,
        method=client.post,
        data={"token": "12345"},
        user=user,
    )
    assert "The entered token is not valid" in str(
        response.context["form"].errors
    )

    # with the correct token, authentication succeeds and user is
    # redirected to the back-up tokens page
    token = get_token_from_totp_device(user.totpdevice_set.get())
    response = get_view_for_user(
        viewname="two-factor-setup",
        client=client,
        method=client.post,
        data={"token": token},
        user=user,
    )
    assert "/accounts/two_factor/backup_tokens" in response.url

    # upon next sign-in 2fa will be prompted
    client.logout()
    response = client.post(
        reverse("account_login"),
        {"login": user.username, "password": SUPER_SECURE_TEST_PASSWORD},
    )
    assert "/accounts/two-factor-authenticate" in response.url

    token = get_token_from_totp_device(user.totpdevice_set.get())
    response = client.post(response.url, {"otp_token": token})
    resp = client.post(response.url)
    assert (
        reverse("profile-detail", kwargs={"username": user.username})
        in resp.url
    )
