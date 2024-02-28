from django.contrib.sites.models import Site
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import EmailSubscriptionTypes


def send_invalid_dockerfile_email(*, container_image):
    container_image.refresh_from_db()

    if container_image.creator:
        message = format_html(
            (
                "Unfortunately we were unable to validate your [docker image]({url}).\n\n"
                "The error message was:\n\n"
                "{status}\n\n"
                "To correct this please upload a new container."
            ),
            url=container_image.get_absolute_url(),
            status=container_image.status,
        )
        site = Site.objects.get_current()
        send_standard_email_batch(
            site=site,
            subject="Could not validate docker image",
            markdown_message=message,
            recipients=[container_image.creator],
            subscription_type=EmailSubscriptionTypes.SYSTEM,
        )
