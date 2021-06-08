from django.conf import settings
from django.core.mail import send_mail
from django.template.defaultfilters import pluralize


def send_unread_notifications_email(recipients):
    subject = "You have unread notifications"

    for user, n_notifications in recipients.items():
        msg = (
            f"Dear {user.user.username},\n\n"
            f"You have {n_notifications} new notification{pluralize(n_notifications)}."
            "To read and manage your notifications, visit: https://grand-challenge.org/notifications/.\n\n"
            "If you no longer wish to receive emails about notifications, you can disable them in your profile settings."
        )
        send_mail(
            subject=subject,
            message=msg,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.user.email],
        )
