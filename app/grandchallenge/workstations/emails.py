from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from config import settings
from grandchallenge.subdomains.utils import reverse


def send_new_feedback_email_to_staff(feedback):
    site = Site.objects.get_current()
    url = reverse(
        "admin:workstations_feedback_change", kwargs={"object_id": feedback.pk}
    )
    message = (
        f"Dear staff,\n\n"
        f"A user just submitted new session feedback. \n\n"
        f"User comment:\n {feedback.user_comment} \n\n"
        f"For more details, see here: {url}.\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    staff = get_user_model().objects.filter(is_staff=True)
    send_mail(
        subject=f"[{site.domain.lower()}] New Session Feedback",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email for user in staff],
    )
