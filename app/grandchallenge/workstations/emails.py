from django.contrib.auth import get_user_model
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.subdomains.utils import reverse


def send_new_feedback_email_to_staff(feedback):
    url = reverse(
        "admin:workstations_feedback_change", kwargs={"object_id": feedback.pk}
    )
    message = format_html(
        (
            "<p>A user just submitted new session feedback.</p>"
            "<p>User comment:</p>"
            "<p>{comment}</p>"
            "<p>For more details, see <a href='{url}'>here</a>.</p>"
        ),
        comment=feedback.user_comment,
        url=url,
    )

    staff = get_user_model().objects.filter(is_staff=True)
    for user in staff:
        send_standard_email_batch(
            subject="New Session Feedback",
            message=message,
            recipients=[user],
        )
