from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.defaultfilters import pluralize

from grandchallenge.subdomains.utils import reverse


def send_unread_notifications_email(recipients):
    site = Site.objects.get_current()
    subject = f"[{site.domain.lower()}] You have unread notifications"
    for profile, n_notifications in recipients.items():
        msg = (
            f"Dear {profile.user.username},\n\n"
            f"You have {n_notifications} new notification{pluralize(n_notifications)}.\n"
            f"To read and manage your notifications, visit: {reverse('notifications:list')}.\n\n"
            f"If you no longer wish to receive emails about notifications, you can disable them in your profile settings: {reverse('profile-update', kwargs={'username': profile.user.username})}.\n\n"
            f"Regards,\n"
            f"{site.name}\n\n"
            f"This is an automated service email from {site.domain.lower()}."
        )
        send_mail(
            subject=subject,
            message=msg,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[profile.user.email],
        )
