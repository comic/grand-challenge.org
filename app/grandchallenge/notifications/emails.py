from django.template.defaultfilters import pluralize
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import SubscriptionTypes
from grandchallenge.subdomains.utils import reverse


def send_unread_notifications_email(*, site, user, n_notifications):
    subject = format_html(
        ("You have {unread_notification_count} new notification{suffix}"),
        unread_notification_count=n_notifications,
        suffix=pluralize(n_notifications),
    )

    msg = format_html(
        (
            "<p>You have {unread_notification_count} new notification{suffix}.</p>"
            "<p>Read and manage your notifications <a href='{url}'>here</a>.</p>"
        ),
        unread_notification_count=n_notifications,
        suffix=pluralize(n_notifications),
        url=reverse("notifications:list"),
    )

    send_standard_email_batch(
        subject=subject,
        message=msg,
        recipients=[user],
        unsubscribable=SubscriptionTypes.NOTIFICATIONS,
    )
