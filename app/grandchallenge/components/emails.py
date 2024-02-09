from django.contrib.sites.models import Site
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email


def send_invalid_dockerfile_email(*, container_image):
    container_image.refresh_from_db()
    site = Site.objects.get_current()

    if container_image.creator:
        message = format_html(
            (
                "Unfortunately we were unable to validate your docker image at "
                "{url}. The error message was:\n\n"
                "{status}\n\n"
                "To correct this please upload a new container.\n\n"
            ),
            url=container_image.get_absolute_url(),
            status=container_image.status,
        )

        send_standard_email(
            site=site,
            subject="Could not validate docker image",
            message=message,
            recipient=container_image.creator,
            unsubscribable=False,
        )
