from django.conf import settings
from django.core.mail import send_mail


def send_unread_notifications_email(recipients):
    subject = "You have unread notifications"

    for user, n_notifications in recipients.items():
        msg = (
            f"Dear {user.user.username},\n\n"
            f"You have {n_notifications} unread notifications."
            "To read them and mark them as read, visit: https://grand-challenge.org/notifications/"
        )
        send_mail(
            subject=subject,
            message=msg,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.user.email],
        )
