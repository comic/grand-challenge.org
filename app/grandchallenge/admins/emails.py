from django.contrib.auth.models import AbstractUser

from core.utils.email import send_templated_email
from grandchallenge.challenges.models import Challenge


def send_new_admin_notification_email(
    *, challenge: Challenge, new_admin: AbstractUser, site
):
    title = f'You are now admin for {challenge.short_name}'
    send_templated_email(
        title,
        "admins/emails/new_admin_notification_email.html",
        {'challenge': challenge, 'new_admin': new_admin, 'site': site},
        [new_admin.email],
    )
