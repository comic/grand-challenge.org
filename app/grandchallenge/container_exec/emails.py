from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail


def send_invalid_dockerfile_email(*, container_image):
    container_image.refresh_from_db()
    site = Site.objects.get_current()

    creator = container_image.creator

    message = (
        f"Dear {{}},\n\n"
        f"Unfortunately we were unable to validate your docker image at "
        f"{container_image.get_absolute_url()}. The "
        f"error message was:\n\n"
        f"{container_image.status}\n\n"
        f"To correct this please upload a new container.\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    recipients = list(get_user_model().objects.filter(is_staff=True))

    if creator:
        recipients.append(creator)

    for recipient in recipients:
        send_mail(
            subject=(
                f"[{site.domain.lower()}] " f"Could not validate docker image"
            ),
            message=message.format(recipient.username),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
        )
