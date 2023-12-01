from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Count, F, Q
from django.template.defaultfilters import pluralize

from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.subdomains.utils import reverse


def get_users_to_send_new_unread_direct_messages_email():
    return (
        get_user_model()
        .objects.prefetch_related(
            "unread_direct_messages__sender", "user_profile"
        )
        .filter(
            user_profile__receive_notification_emails=True,
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
    *, site, username, email, new_senders, new_unread_message_count
):
    subject = f"[{site.domain.lower()}] You have {new_unread_message_count} new message{pluralize(new_unread_message_count)} from {oxford_comma(new_senders)}"

    msg = (
        f"Dear {username},\n\n"
        f"You have {new_unread_message_count} new message{pluralize(new_unread_message_count)} from {oxford_comma(new_senders)}.\n"
        f"To read and manage your messages, visit: {reverse('direct-messages:conversation-list')}.\n\n"
        f"If you no longer wish to receive notification emails, you can disable them in your profile settings: {reverse('profile-update', kwargs={'username': username})}.\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain.lower()}."
    )

    send_mail(
        subject=subject,
        message=msg,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
