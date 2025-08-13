import pytest
from django.conf import settings

from grandchallenge.profiles.models import (
    BannedEmailAddress,
    NotificationEmailOptions,
)
from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_signup_disallowed_for_banned_email(client):
    banned_email = "foo@bar.com"

    BannedEmailAddress(email=banned_email.upper()).save()

    response = client.post(reverse("dummy_login"))
    response = client.post(
        response["location"],
        {
            "id": "2",
            "email": banned_email,
            "email_verified": True,
            "username": "dummy_user",
        },
    )

    assert response.status_code == 403
    assert "This email address is not allowed." in response.content.decode()


@pytest.mark.django_db
def test_password_can_be_reset_with_verification(client):
    user = UserFactory()
    VerificationFactory(user=user, email=user.email)

    response = client.post(
        reverse("account_reset_password"), {"email": user.email}
    )

    assert response.status_code == 302
    assert f"https://testserver{response.url}" == reverse(
        "account_reset_password_done"
    )


@pytest.mark.django_db
def test_password_can_be_reset_with_banned_domain(client):
    # User has legacy account from banned domain
    user = UserFactory(email=f"test@{[*settings.DISALLOWED_EMAIL_DOMAINS][0]}")

    response = client.post(
        reverse("account_reset_password"), {"email": user.email}
    )

    assert response.status_code == 302
    assert f"https://testserver{response.url}" == reverse(
        "account_reset_password_done"
    )


SIGNUP_DATA = {
    "first_name": "test",
    "last_name": "test",
    "username": "test321455",
    "email": "test@example.org",
    "email2": "test@example.org",
    "password1": "testpassword",
    "password2": "testpassword",
    "institution": "test",
    "department": "test",
    "country": "NL",
    "website": "https://www.example.com",
    "only_account": True,
    "notification_email_choice": NotificationEmailOptions.DAILY_SUMMARY,
}


@pytest.mark.django_db
def test_account_cannot_be_made_with_existing_verification(client):
    VerificationFactory(email=SIGNUP_DATA["email"])

    response = client.post(reverse("account_signup"), SIGNUP_DATA)

    assert response.status_code == 200
    assert response.context["form"].errors == {
        "email": ["This email address is already in use."],
    }


@pytest.mark.django_db
def test_account_cannot_be_made_with_banned_email(client):
    BannedEmailAddress(email=SIGNUP_DATA["email"]).save()

    response = client.post(reverse("account_signup"), SIGNUP_DATA)

    assert response.status_code == 200
    assert response.context["form"].errors == {
        "email": ["This email address is not allowed."],
    }
