from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import format_html


def send_standard_email(*, site, subject, message, recipient, unsubscribable):
    if not recipient.is_active:
        # Do not send emails to inactive users
        return

    if (
        unsubscribable
        and not recipient.user_profile.receive_notification_emails
    ):
        # Do not send unsubscribable emails to users who have opted out
        return

    send_mail(
        subject=format_html(
            "[{domain}] {subject}", domain=site.domain.lower(), subject=subject
        ),
        message=render_to_string(
            "emails/standard_email.txt",
            context={
                "recipient": recipient,
                "message": message,
                "site": site,
                "unsubscribable": unsubscribable,
            },
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient.email],
    )
