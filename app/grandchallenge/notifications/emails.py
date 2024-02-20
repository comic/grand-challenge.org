from django.template.defaultfilters import pluralize
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email
from grandchallenge.subdomains.utils import reverse


def send_unread_notifications_email(*, site, user, n_notifications):
    subject = format_html(
        ("You have {unread_notification_count} new notification{suffix}"),
        unread_notification_count=n_notifications,
        suffix=pluralize(n_notifications),
    )

    msg = format_html(
        (
            "You have {unread_notification_count} new notification{suffix}.\n"
            "To read and manage your notifications, visit: {url}.\n\n"
        ),
        unread_notification_count=n_notifications,
        suffix=pluralize(n_notifications),
        url=reverse("notifications:list"),
    )

    send_standard_email(
        site=site,
        subject=subject,
        message=msg,
        recipient=user,
        unsubscribable=True,
    )
