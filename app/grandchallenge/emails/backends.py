from django.core.mail.backends.base import BaseEmailBackend
from django.db.transaction import on_commit

from grandchallenge.emails.models import RawEmail
from grandchallenge.emails.tasks import send_raw_email


class CelerySESBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        for email_message in email_messages:
            raw_email = RawEmail.objects.create(
                message=email_message.message().as_string()
            )
            on_commit(
                send_raw_email.signature(
                    kwargs={"raw_email_pk": raw_email.pk}
                ).apply_async
            )
        return len(email_messages)
