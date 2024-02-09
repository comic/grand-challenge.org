from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email
from grandchallenge.subdomains.utils import reverse


def send_new_feedback_email_to_staff(feedback):
    site = Site.objects.get_current()
    url = reverse(
        "admin:workstations_feedback_change", kwargs={"object_id": feedback.pk}
    )
    message = format_html(
        (
            "A user just submitted new session feedback. \n\n"
            "User comment:\n {comment} \n\n"
            "For more details, see here: {url}.\n\n"
        ),
        comment=feedback.user_comment,
        url=url,
    )

    staff = get_user_model().objects.filter(is_staff=True)
    for user in staff:
        send_standard_email(
            site=site,
            subject="New Session Feedback",
            message=message,
            recipient=user,
            unsubscribable=False,
        )
