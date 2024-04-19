import pytest
from django.core import mail

from tests.factories import UserFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_email_sent_to_correct_email():
    user = UserFactory(email="personal@example.org")
    VerificationFactory(email="institutional@example.org", user=user)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["institutional@example.org"]
    assert (
        mail.outbox[0].subject
        == "[testserver] Please confirm your email address for account validation"
    )
