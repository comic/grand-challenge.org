from django.template.defaultfilters import pluralize
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.subdomains.utils import reverse


def send_unread_notifications_email(*, site, user, n_notifications):
    # local import to avoid circular dependency
    from grandchallenge.profiles.models import EmailSubscriptionTypes

    subject = format_html(
        ("You have {unread_notification_count} new notification{suffix}"),
        unread_notification_count=n_notifications,
        suffix=pluralize(n_notifications),
    )

    msg = format_html(
        (
            "You have {unread_notification_count} new notification{suffix}.\n\n"
            "Read and manage your notifications [here]({url})."
        ),
        unread_notification_count=n_notifications,
        suffix=pluralize(n_notifications),
        url=reverse("notifications:list"),
    )
    send_standard_email_batch(
        site=site,
        subject=subject,
        markdown_message=msg,
        recipients=[user],
        subscription_type=EmailSubscriptionTypes.NOTIFICATION,
    )
