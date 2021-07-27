from django.contrib.sites.models import Site
from django.core.mail import mail_managers

from grandchallenge.subdomains.utils import reverse


def send_challenge_created_email(challenge):
    site = Site.objects.get_current()
    message = (
        f"Dear manager,\n\n"
        f"User {challenge.creator} has just created the challenge "
        f"{challenge.short_name} at {challenge.get_absolute_url()}.\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    mail_managers(
        subject=f"[{site.domain.lower()}] New Challenge Created",
        message=message,
    )


def send_external_challenge_created_email(challenge):
    site = Site.objects.get_current()
    update_url = reverse(
        "challenges:external-update",
        kwargs={"short_name": challenge.short_name},
    )

    message = (
        f"Dear manager,\n\n"
        f"User {challenge.creator} has just created the challenge "
        f"{challenge.short_name}. You need to un-hide it before it is visible "
        f"on the all challenges page, you can do that here: {update_url}\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    mail_managers(
        subject=f"[{site.domain.lower()}] New External Challenge",
        message=message,
    )
