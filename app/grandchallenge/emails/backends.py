from django.core.mail.backends.base import BaseEmailBackend

from grandchallenge.emails.models import RawEmail


class CelerySESBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raw_emails = RawEmail.objects.bulk_create(
            [
                RawEmail(message=email_message.message().as_string())
                for email_message in email_messages
            ]
        )
        return len(raw_emails)
