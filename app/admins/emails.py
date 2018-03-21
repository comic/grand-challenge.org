from django.contrib.auth.models import AbstractUser

from challenges.models import ComicSite
from core.utils.email import send_templated_email


def send_new_admin_notification_email(
    *, challenge: ComicSite, new_admin: AbstractUser, site
):
    title = f'You are now admin for {challenge.short_name}'
    send_templated_email(
        title,
        "admins/emails/new_admin_notification_email.html",
        {'challenge': challenge, 'new_admin': new_admin, 'site': site},
        [new_admin.email],
    )
