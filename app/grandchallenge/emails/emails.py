from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import format_html

from grandchallenge.profiles.models import EmailSubscriptionTypes
from grandchallenge.subdomains.utils import reverse


def filter_recipients(*, recipients, subscription_type):
    filtered_recipients = []
    for recipient in recipients:
        if not recipient.is_active:
            # Do not send emails to inactive users
            continue

        if (
            subscription_type == EmailSubscriptionTypes.NOTIFICATION
            and not recipient.user_profile.receive_notification_emails
        ) or (
            subscription_type == EmailSubscriptionTypes.NEWSLETTER
            and not recipient.user_profile.receive_newsletter
        ):
            # Do not send emails to users who have opted out
            continue

        filtered_recipients.append(recipient)

    return filtered_recipients


def send_standard_email_batch(
    *, site, subject, markdown_message, recipients, subscription_type
):
    connection = get_connection()
    messages = []
    recipients = filter_recipients(
        recipients=recipients, subscription_type=subscription_type
    )
    for recipient in recipients:
        messages.append(
            create_email_object(
                recipient=recipient,
                site=site,
                subject=subject,
                markdown_message=markdown_message,
                subscription_type=subscription_type,
                connection=connection,
            )
        )
    return connection.send_messages(messages)


def get_unsubscribe_link(*, recipient, subscription_type):
    if subscription_type == EmailSubscriptionTypes.NEWSLETTER:
        return reverse(
            "newsletter-unsubscribe",
            kwargs={"token": recipient.user_profile.unsubscribe_token},
        )
    elif subscription_type == EmailSubscriptionTypes.NOTIFICATION:
        return reverse(
            "notification-unsubscribe",
            kwargs={"token": recipient.user_profile.unsubscribe_token},
        )
    elif subscription_type == EmailSubscriptionTypes.SYSTEM:
        return None
    else:
        return NotImplementedError(
            f"Unknown subscription type: {subscription_type}"
        )


def get_headers(*, unsubscribe_link):
    if unsubscribe_link:
        return {
            "List-Unsubscribe": unsubscribe_link,
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    else:
        return None


def create_email_object(
    *,
    recipient,
    site,
    subject,
    markdown_message,
    connection,
    subscription_type,
):
    unsubscribe_link = get_unsubscribe_link(
        recipient=recipient, subscription_type=subscription_type
    )
    headers = get_headers(unsubscribe_link=unsubscribe_link)

    html_content = render_to_string(
        "vendored/mailgun_transactional_emails/action.html",
        {
            "title": subject,
            "username": recipient.username,
            "content": markdown_message,
            "unsubscribe_link": unsubscribe_link,
            "subscription_type": subscription_type,
            "site": site,
        },
    )
    text_content = render_to_string(
        "emails/standard_plaintext_email.txt",
        {
            "username": recipient.username,
            "content": markdown_message,
            "unsubscribe_link": unsubscribe_link,
            "subscription_type": subscription_type,
            "site": site,
        },
    )
    html_content_without_linebreaks = html_content.replace("\n", "")

    email = EmailMultiAlternatives(
        subject=format_html(
            "[{domain}] {subject}", domain=site.domain.lower(), subject=subject
        ),
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient.email],
        connection=connection,
        headers=headers,
    )
    email.attach_alternative(html_content_without_linebreaks, "text/html")
    return email
