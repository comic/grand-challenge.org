import pytest

from grandchallenge.profiles.models import BannedEmailAddress
from tests.factories import UserFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_primary_email_banned_on_delete():
    u = UserFactory()

    email = u.email
    username = u.username

    u.delete()

    ban = BannedEmailAddress.objects.get(email=email)
    assert f"Primary email address of deleted user {username}" in ban.reason


@pytest.mark.django_db
def test_verification_email_banned_on_delete():
    u = UserFactory()
    v = VerificationFactory(user=u, email_is_verified=True)

    email = v.email
    username = u.username

    u.delete()

    ban = BannedEmailAddress.objects.get(email=email)
    assert (
        ban.reason
        == f"Verified verification email address of deleted user {username}"
    )


@pytest.mark.django_db
def test_verification_email_not_banned_on_delete():
    u = UserFactory()
    v = VerificationFactory(user=u, email_is_verified=False)

    email = v.email

    u.delete()

    assert not BannedEmailAddress.objects.filter(email=email).exists()
