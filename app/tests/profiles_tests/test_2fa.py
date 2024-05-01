import pytest
from allauth.mfa.models import Authenticator
from django.core import mail
from django.test import override_settings
from django.utils.http import int_to_base36

from grandchallenge.subdomains.utils import reverse, reverse_lazy
from tests.factories import SUPER_SECURE_TEST_PASSWORD, UserFactory
from tests.utils import get_view_for_user


def get_totp_token(user):
    device = Authenticator.objects.get(
        user=user, type=Authenticator.Type.RECOVERY_CODES
    )
    return device.wrap().get_unused_codes()[0]


@pytest.mark.django_db
def test_2fa_required_for_staff(client):
    admin = UserFactory(is_staff=True)
    user = UserFactory()

    response = get_view_for_user(
        viewname="home",
        client=client,
        user=user,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="home",
        client=client,
        user=admin,
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
    user = UserFactory(is_staff=True)
    resp = get_view_for_user(
        viewname=url,
        reverse_kwargs=url_kwargs,
        client=client,
        user=user if login_required else None,
    )
    assert resp.status_code == expected_status_code
    if expected_status_code == 302:
        assert resp["location"] != reverse("mfa_activate_totp")


@override_settings(ACCOUNT_EMAIL_VERIFICATION=None)
@pytest.mark.django_db
def test_email_after_2fa_login_for_staff(client, user_with_totp):
    staff = user_with_totp(is_staff=True)
    client.post(
        reverse("account_login"),
        {"login": staff.username, "password": SUPER_SECURE_TEST_PASSWORD},
    )
    client.post(
        reverse_lazy("mfa_authenticate"), {"code": get_totp_token(staff)}
    )
    assert len(mail.outbox) == 1
    assert "Security Alert" in mail.outbox[0].subject
    assert "We noticed a new login to your account." in mail.outbox[0].body
    assert mail.outbox[0].to == [staff.email]

    mail.outbox.clear()
    user = user_with_totp()
    client.post(
        reverse("account_login"),
        {"login": user.username, "password": SUPER_SECURE_TEST_PASSWORD},
    )
    client.post(
        reverse_lazy("mfa_authenticate"), {"code": get_totp_token(user)}
    )
    assert len(mail.outbox) == 0
