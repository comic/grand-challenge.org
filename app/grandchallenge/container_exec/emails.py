from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail


def send_invalid_dockerfile_email(*, container_image):
    container_image.refresh_from_db()

    creator = container_image.creator

    message = (
        f"Dear {container_image.creator},\n\n"
        f"Unfortunately we were unable to validate your docker image at "
        f"{container_image.get_absolute_url()}. The "
        f"error message was:\n\n"
        f"{container_image.status}\n\n"
        f"To correct this please upload a new container."
    )

    recipient_emails = [
        s.email for s in get_user_model().objects.filter(is_staff=True)
    ]

    if creator:
        recipient_emails.append(container_image.creator.email)

    for email in recipient_emails:
        send_mail(
            subject=(
                f"[{Site.objects.get_current().domain.lower()}] "
                f"Could not validate docker image"
            ),
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
