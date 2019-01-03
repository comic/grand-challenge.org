from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.subdomains.utils import reverse


def send_challenge_created_email(challenge: Challenge):
    message = (
        f"Dear staff,\n\n"
        f"User {challenge.creator} has just created the challenge "
        f"{challenge.short_name} at {challenge.get_absolute_url()}."
    )

    staff = get_user_model().objects.filter(is_staff=True)

    for s in staff:
        send_mail(
            subject="New Challenge Created",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[s.email],
        )


def send_external_challenge_created_email(challenge: ExternalChallenge):
    update_url = reverse(
        "challenges:external-update",
        kwargs={"short_name": challenge.short_name},
    )

    message = (
        f"Dear staff,\n\n"
        f"User {challenge.creator} has just created the challenge "
        f"{challenge.short_name}. You need to un-hide it before it is visible "
        f"on the all challenges page, you can do that here: {update_url}"
    )

    staff = get_user_model().objects.filter(is_staff=True)

    for s in staff:
        send_mail(
            subject="New External Challenge",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[s.email],
        )
