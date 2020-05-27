from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail


def send_invalid_dockerfile_email(*, container_image):
    container_image.refresh_from_db()
    site = Site.objects.get_current()

    creator = container_image.creator
    creator_username = creator.username if creator else "unknown"

    creator_message = (
        f"Dear {creator_username},\n\n"
        f"Unfortunately we were unable to validate your docker image at "
        f"{container_image.get_absolute_url()}. The "
        f"error message was:\n\n"
        f"{container_image.status}\n\n"
        f"To correct this please upload a new container.\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    staff_message = (
        f"Dear {{}},\n\n"
        f"Unfortunately we were unable to validate the docker image uploaded by {creator_username} "
        f"at {container_image.get_absolute_url()}. The "
        f"error message was:\n\n"
        f"{container_image.status}\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"You receive this automated service email because you "
        f"are a staff member of {site.domain}."
    )

    recipients = list(get_user_model().objects.filter(is_staff=True))
    if creator:
        send_mail(
            subject=(
                f"[{site.domain.lower()}] " f"Could not validate docker image"
            ),
            message=creator_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[creator.email],
        )

    for recipient in recipients:
        send_mail(
            subject=(
                f"[{site.domain.lower()}] " f"Could not validate docker image"
            ),
            message=staff_message.format(recipient.username),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
        )
