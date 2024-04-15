from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import format_html


def send_standard_email_batch(
    *, site, subject, markdown_message, recipients, subscription_type
):
    connection = get_connection()
    messages = []

    for recipient in recipients:
        try:
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
        except ValueError:
            # Raised if the user cannot be emailed due to
            # preferences or blocked status
            continue

    return connection.send_messages(messages)


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
    unsubscribe_link = recipient.user_profile.get_unsubscribe_link(
        subscription_type=subscription_type
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
    email.attach_alternative(html_content, "text/html")
    return email
