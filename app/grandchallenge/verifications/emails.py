from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from grandchallenge.verifications.models import Verification


def send_verification_email(*, verification: Verification):
    site = Site.objects.get_current()
    message = (
        f"Dear {verification.user.username},\n\n"
        "Please confirm this email address by visiting the following link: "
        f"{verification.verification_url}\n\n"
        "Please disregard this email if you did not make this confirmation "
        "request.\n\n"
        "Regards,\n"
        f"{site.name}\n"
        f"This is an automated service email from {site.domain}."
    )
    send_mail(
        subject=f"[{site.domain.lower()}] Please confirm your email address",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[verification.email],
        message=message,
    )
