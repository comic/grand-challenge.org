from django.contrib.auth.models import AbstractUser

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.utils.email import send_templated_email


def send_new_admin_notification_email(
    *, challenge: Challenge, new_admin: AbstractUser, site
):
    title = f"[{challenge.short_name.lower()}] You Are Now An Admin"
    send_templated_email(
        title,
        "admins/emails/new_admin_notification_email.html",
        {"challenge": challenge, "new_admin": new_admin, "site": site},
        [new_admin.email],
    )
