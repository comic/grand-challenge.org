import pytest

from grandchallenge.profiles.models import BannedEmailAddress
from grandchallenge.subdomains.utils import reverse


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
