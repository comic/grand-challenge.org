from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch


def send_invalid_dockerfile_email(*, container_image):
    container_image.refresh_from_db()

    if container_image.creator:
        message = format_html(
            (
                "<p>Unfortunately we were unable to validate your docker image at "
                "{url}. The error message was:</p>"
                "<pre>{status}</pre>"
                "<p>To correct this please upload a new container.</p>"
            ),
            url=container_image.get_absolute_url(),
            status=container_image.status,
        )

        send_standard_email_batch(
            subject="Could not validate docker image",
            message=message,
            recipients=[container_image.creator],
        )
