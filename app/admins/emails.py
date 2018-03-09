from django.contrib.auth.models import AbstractUser

from comicmodels.models import ComicSite
from comicsite.utils.email import send_templated_email


def send_new_admin_notification_email(*, challenge: ComicSite,
                                      new_admin: AbstractUser,
                                      site):
    title = f'You are now admin for {challenge.short_name}'
    send_templated_email(
        title,
        "admins/emails/new_admin_notification_email.html",
        {
            'comicsite': challenge,
            'new_admin': new_admin,
            'site': site,
        },
        [new_admin.email])
