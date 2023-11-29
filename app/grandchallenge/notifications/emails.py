from django.conf import settings
from django.core.mail import send_mail
from django.template.defaultfilters import pluralize

from grandchallenge.subdomains.utils import reverse


def send_unread_notifications_email(*, site, username, email, n_notifications):
    subject = f"[{site.domain.lower()}] You have {n_notifications} new notification{pluralize(n_notifications)}"

    msg = (
        f"Dear {username},\n\n"
        f"You have {n_notifications} new notification{pluralize(n_notifications)}.\n"
        f"To read and manage your notifications, visit: {reverse('notifications:list')}.\n\n"
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
