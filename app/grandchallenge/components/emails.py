from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail


def send_invalid_dockerfile_email(*, container_image):
    container_image.refresh_from_db()
    site = Site.objects.get_current()

    if container_image.creator:
        message = (
            f"Dear {container_image.creator.username},\n\n"
            f"Unfortunately we were unable to validate your docker image at "
            f"{container_image.get_absolute_url()}. The "
            f"error message was:\n\n"
            f"{container_image.status}\n\n"
            f"To correct this please upload a new container.\n\n"
            f"Regards,\n"
            f"{site.name}\n\n"
            f"This is an automated service email from {site.domain}."
        )

        send_mail(
            subject=(
                f"[{site.domain.lower()}] Could not validate docker image"
            ),
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[container_image.creator.email],
        )
