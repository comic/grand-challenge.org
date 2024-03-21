from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q
from django.template.defaultfilters import pluralize
from django.utils.html import format_html

from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import NotificationEmailOptions
from grandchallenge.subdomains.utils import reverse


def get_users_to_send_new_unread_direct_messages_email():
    return (
        get_user_model()
        .objects.prefetch_related(
            "unread_direct_messages__sender", "user_profile"
        )
        .filter(
            user_profile__notification_email_choice=NotificationEmailOptions.DAILY_SUMMARY,
            is_active=True,
        )
        .annotate(
            new_unread_message_count=Count(
                "unread_direct_messages",
                filter=Q(
                    user_profile__unread_messages_email_last_sent_at__isnull=True
                )
                | Q(
                    unread_direct_messages__created__gt=F(
                        "user_profile__unread_messages_email_last_sent_at"
                    )
                ),
            )
        )
        .filter(new_unread_message_count__gt=0)
    )


def get_new_senders(*, user):
    new_senders = {
        message.sender
        for message in user.unread_direct_messages.all()
        if (
            user.user_profile.unread_messages_email_last_sent_at is None
            or message.created
            > user.user_profile.unread_messages_email_last_sent_at
        )
    }
    return sorted(list(new_senders), key=lambda s: s.pk)


def send_new_unread_direct_messages_email(
    *, site, user, new_senders, new_unread_message_count
):
    # local import to avoid circular dependency
    from grandchallenge.profiles.models import EmailSubscriptionTypes

    subject = format_html(
        (
            "You have {new_unread_message_count} new message{suffix} "
            "from {new_senders}"
        ),
        new_unread_message_count=new_unread_message_count,
        suffix=pluralize(new_unread_message_count),
        new_senders=oxford_comma(new_senders),
    )

    msg = format_html(
        (
            "You have {new_unread_message_count} new message{suffix} from {new_senders}.\n\n"
            "To read and manage your messages, click [here]({url})."
        ),
        new_unread_message_count=new_unread_message_count,
        suffix=pluralize(new_unread_message_count),
        new_senders=oxford_comma(new_senders),
        url=reverse("direct-messages:conversation-list"),
    )
    send_standard_email_batch(
        site=site,
        subject=subject,
        markdown_message=msg,
        recipients=[user],
        subscription_type=EmailSubscriptionTypes.NOTIFICATION,
    )
