from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from comicmodels.models import ComicSite


def send_challenge_created_email(challenge: ComicSite):
    message = (
        f'Dear staff,\n\n'
        f'User {challenge.creator} has just created the challenge '
        f'{challenge.short_name} at {challenge.get_absolute_url()}.'
    )

    staff = get_user_model().objects.filter(is_staff=True)

    for s in staff:
        send_mail(
            subject='New Challenge Created',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[s.email],
        )
