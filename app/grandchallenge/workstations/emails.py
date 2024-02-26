from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import EmailSubscriptionTypes
from grandchallenge.subdomains.utils import reverse


def send_new_feedback_email_to_staff(feedback):
    url = reverse(
        "admin:workstations_feedback_change", kwargs={"object_id": feedback.pk}
    )
    message = format_html(
        (
            "A user just submitted new session feedback.\n\n"
            "User comment:\n\n"
            "{comment}\n\n"
            "For more details, see [here]({url})."
        ),
        comment=feedback.user_comment,
        url=url,
    )

    staff = get_user_model().objects.filter(is_staff=True)
    site = Site.objects.get_current()
    for user in staff:
        send_standard_email_batch(
            site=site,
            subject="New Session Feedback",
            markdown_message=message,
            recipients=[user],
            subscription_type=EmailSubscriptionTypes.SYSTEM,
        )
