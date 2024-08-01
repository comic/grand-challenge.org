import pytest
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils.crypto import get_random_string
from django.utils.http import int_to_base36

from grandchallenge.core.utils.list_url_names import list_url_names
from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory, activate_2fa
from tests.utils import get_view_for_user


def get_unused_recovery_token(user):
    device = Authenticator.objects.get(
        user=user, type=Authenticator.Type.RECOVERY_CODES
    )
    return device.wrap().get_unused_codes()[0]


@pytest.mark.django_db
def test_2fa_required_for_staff(client):
    user = UserFactory()

    response = get_view_for_user(
        viewname="home",
        client=client,
        user=user,
    )
    assert response.status_code == 200

    # Make the user staff, should then be asked to activate 2fa
    user.is_staff = True
    user.save()

    response = get_view_for_user(
        viewname="home",
        client=client,
        user=user,
    )
    assert response.status_code == 302
    assert "/accounts/2fa/totp/activate/" in response.url


@pytest.mark.parametrize(
    "url, url_kwargs, login_required, expected_status_code",
    [
        ("account_login", None, False, 200),
        ("account_signup", None, False, 200),
        ("account_logout", None, False, 302),
        ("account_reauthenticate", None, True, 200),
        ("account_email", None, True, 200),
        ("account_email_verification_sent", None, True, 200),
        ("account_confirm_email", {"key": "abcd1234"}, True, 200),
        ("account_change_password", None, True, 200),
        ("account_set_password", None, True, 302),
        ("account_inactive", None, True, 200),
        ("account_reset_password", None, True, 200),
        ("account_reset_password_done", None, True, 200),
        (
            "account_reset_password_from_key",
            {"uidb36": int_to_base36(1234), "key": "abcd1234"},
            True,
            200,
        ),
        ("account_reset_password_from_key_done", None, True, 200),
        ("socialaccount_login_cancelled", None, True, 200),
        ("socialaccount_login_error", None, True, 200),
        ("socialaccount_connections", None, True, 200),
        ("mfa_activate_totp", None, True, 302),
        ("mfa_index", None, True, 200),
    ],
)
@pytest.mark.django_db
def test_require_mfa_not_on_allowed_urls(
    client,
    url,
    url_kwargs,
    login_required,
    expected_status_code,
):
    staff_user = UserFactory(is_staff=True)
    resp = get_view_for_user(
        viewname=url,
        reverse_kwargs=url_kwargs,
        client=client,
        user=staff_user if login_required else None,
    )
    assert resp.status_code == expected_status_code
    if expected_status_code == 302:
        assert resp["location"] != reverse("mfa_activate_totp")


@pytest.mark.django_db
def test_email_after_2fa_login_for_staff(client):
    password = get_random_string(32)

    staff_user = UserFactory(is_staff=True, password=password)

    EmailAddress.objects.create(
        user=staff_user, email=staff_user.email, verified=True
    )

    response = client.post(
        reverse("account_login"),
        {"login": staff_user.username, "password": password},
    )

    # Should be redirected to 2fa authentication
    assert response.status_code == 302
    assert "/accounts/2fa/authenticate/" in response.url

    response = client.post(
        response.url, {"code": get_unused_recovery_token(staff_user)}
    )

    assert response["location"] == settings.LOGIN_REDIRECT_URL
    assert len(mail.outbox) == 1
    assert "Security Alert" in mail.outbox[0].subject
    assert "We noticed a new login to your account." in mail.outbox[0].body
    assert mail.outbox[0].to == [staff_user.email]


@pytest.mark.django_db
def test_no_email_after_2fa_login_for_non_staff(client):
    password = get_random_string(32)

    user = UserFactory(password=password)
    activate_2fa(user=user)

    EmailAddress.objects.create(user=user, email=user.email, verified=True)

    response = client.post(
        reverse("account_login"),
        {"login": user.username, "password": password},
    )

    # Should be redirected to 2fa authentication
    assert response.status_code == 302
    assert "/accounts/2fa/authenticate/" in response.url

    response = client.post(
        response.url, {"code": get_unused_recovery_token(user)}
    )

    assert response["location"] == settings.LOGIN_REDIRECT_URL
    assert len(mail.outbox) == 0


def test_allowed_urls():
    assert list_url_names("allauth.urls") == {
        "account_signup",
        "account_email_verification_sent",
        "mfa_reauthenticate",
        "mfa_download_recovery_codes",
        "mfa_view_recovery_codes",
        "socialaccount_connections",
        "account_inactive",
        "account_reset_password_done",
        "account_reset_password_from_key",
        "mfa_deactivate_totp",
        "socialaccount_login_cancelled",
        "account_reauthenticate",
        "account_email",
        "gmail_callback",
        "account_logout",
        "mfa_index",
        "account_login",
        "socialaccount_login_error",
        "account_reset_password",
        "account_reset_password_from_key_done",
        "mfa_generate_recovery_codes",
        "gmail_login",
        "account_change_password",
        "mfa_activate_totp",
        "socialaccount_signup",
        "account_confirm_email",
        "mfa_authenticate",
        "account_set_password",
        "dummy_login",
        "dummy_authenticate",
    }


@override_settings(SOCIALACCOUNT_AUTO_SIGNUP=True)
@pytest.mark.django_db
def test_2fa_for_for_staff_users_with_social_login(client):
    resp = client.post(reverse("dummy_login"))
    resp = client.post(
        resp["location"],
        {
            "id": "2",
            "email": "a@b.com",
            "email_verified": True,
            "username": "foo",
        },
    )
    assert resp.status_code == 302
    assert resp["location"] == settings.LOGIN_REDIRECT_URL

    user_with_social_account = (
        get_user_model().objects.filter(username="foo").get()
    )
    user_with_social_account.is_staff = True
    user_with_social_account.save()

    # User is now staff, should activate mfa
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/accounts/2fa/totp/activate/" in resp.url

    # enable 2fa for the user
    activate_2fa(user=user_with_social_account)

    # logout and login again, should be asked to MFA authenticate
    client.logout()
    resp = client.post(reverse("dummy_login"))
    resp = client.post(resp["location"], {"id": "2"})
    assert resp.status_code == 302
    assert "/accounts/2fa/authenticate/" in resp.url

    token = get_unused_recovery_token(user_with_social_account)
    resp = client.post(resp.url, {"code": token})
    assert resp["location"] == settings.LOGIN_REDIRECT_URL
