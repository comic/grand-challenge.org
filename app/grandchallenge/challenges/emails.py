from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.subdomains.utils import reverse


def send_challenge_created_email(challenge: Challenge):
    site = Site.objects.get_current()
    message = (
        f"Dear {{}},\n\n"
        f"User {challenge.creator} has just created the challenge "
        f"{challenge.short_name} at {challenge.get_absolute_url()}.\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    staff = get_user_model().objects.filter(is_staff=True)

    for s in staff:
        send_mail(
            subject=f"[{site.domain.lower()}] New Challenge Created",
            message=message.format(s.username),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[s.email],
        )


def send_external_challenge_created_email(challenge: ExternalChallenge):
    site = Site.objects.get_current()
    update_url = reverse(
        "challenges:external-update",
        kwargs={"short_name": challenge.short_name},
    )

    message = (
        f"Dear {{}},\n\n"
        f"User {challenge.creator} has just created the challenge "
        f"{challenge.short_name}. You need to un-hide it before it is visible "
        f"on the all challenges page, you can do that here: {update_url}\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    staff = get_user_model().objects.filter(is_staff=True)

    for s in staff:
        send_mail(
            subject=f"[{site.domain.lower()}] New External Challenge",
            message=message.format(s.username),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[s.email],
        )
