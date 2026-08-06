import pytest
from django.contrib.sites.models import Site

from grandchallenge.emails.admin import send_to_me
from grandchallenge.emails.models import Email
from tests.emails_tests.factories import EmailFactory
from tests.factories import UserFactory


@pytest.mark.django_db
class TestSendToMeAction:
    def test_sends_email_to_current_user(self, mailoutbox):
        admin_user = UserFactory(is_staff=True, is_superuser=True)
        email = EmailFactory(
            subject="Test Subject",
            body="Test body content",
            status=Email.EmailStatusChoices.INITIALIZED,
        )

        class MockRequest:
            user = admin_user

        class MockModelAdmin:
            pass

        send_to_me(
            MockModelAdmin(),
            MockRequest(),
            Email.objects.filter(pk=email.pk),
        )

        assert len(mailoutbox) == 1
        site = Site.objects.get_current()
        assert f"[{site.domain.lower()}] Test Subject" in mailoutbox[0].subject
        assert mailoutbox[0].to == [admin_user.email]

    def test_does_not_change_email_status(self, mailoutbox):
        email = EmailFactory(
            subject="Test Subject",
            body="Test body content",
            status=Email.EmailStatusChoices.INITIALIZED,
        )

        admin_user = UserFactory(is_staff=True, is_superuser=True)

        class MockRequest:
            user = admin_user

        class MockModelAdmin:
            pass

        send_to_me(
            MockModelAdmin(),
            MockRequest(),
            Email.objects.filter(pk=email.pk),
        )

        email.refresh_from_db()
        assert email.status == Email.EmailStatusChoices.INITIALIZED

    def test_sends_multiple_emails_to_current_user(self, mailoutbox):
        admin_user = UserFactory(is_staff=True, is_superuser=True)
        EmailFactory(
            subject="Subject 1",
            body="Body 1",
            status=Email.EmailStatusChoices.INITIALIZED,
        )
        EmailFactory(
            subject="Subject 2",
            body="Body 2",
            status=Email.EmailStatusChoices.INITIALIZED,
        )

        class MockRequest:
            user = admin_user

        class MockModelAdmin:
            pass

        send_to_me(
            MockModelAdmin(),
            MockRequest(),
            Email.objects.all(),
        )

        assert len(mailoutbox) == 2
        assert all(msg.to == [admin_user.email] for msg in mailoutbox)

    def test_sends_regardless_of_email_status(self, mailoutbox):
        admin_user = UserFactory(is_staff=True, is_superuser=True)
        EmailFactory(
            subject="Queued Email",
            body="Body",
            status=Email.EmailStatusChoices.QUEUED,
        )
        EmailFactory(
            subject="Succeeded Email",
            body="Body",
            status=Email.EmailStatusChoices.SUCCEEDED,
        )

        class MockRequest:
            user = admin_user

        class MockModelAdmin:
            pass

        send_to_me(
            MockModelAdmin(),
            MockRequest(),
            Email.objects.all(),
        )

        assert len(mailoutbox) == 2
