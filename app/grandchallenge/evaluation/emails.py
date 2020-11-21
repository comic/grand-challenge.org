from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from grandchallenge.subdomains.utils import reverse


def send_failed_evaluation_email(evaluation):
    site = Site.objects.get_current()
    message = (
        f"Dear {{}},\n\n"
        f"Unfortunately the evaluation for the submission to "
        f"{evaluation.submission.phase.challenge.short_name} failed with an "
        f"error. The error message is:\n\n"
        f"{evaluation.error_message}\n\n"
        f"You may wish to try and correct this, or contact the challenge "
        f"organizers. The following information may help them:\n"
        f"User: {evaluation.submission.creator.username}\n"
        f"Evaluation ID: {evaluation.pk}\n"
        f"Submission ID: {evaluation.submission.pk}\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )
    recipients = list(evaluation.submission.phase.challenge.get_admins())
    recipients.append(evaluation.submission.creator)
    for recipient in recipients:
        send_mail(
            subject=(
                f"[{site.domain.lower()}] "
                f"[{evaluation.submission.phase.challenge.short_name.lower()}] "
                f"Evaluation Failed"
            ),
            message=message.format(recipient.username),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
        )


def send_successful_evaluation_email(evaluation):
    site = Site.objects.get_current()
    challenge = evaluation.submission.phase.challenge

    recipients = list(challenge.get_admins())
    message = (
        f"Dear {{}},\n\n"
        f"There is a new result for {challenge.short_name} from "
        f"{evaluation.submission.creator.username}. "
    )
    if evaluation.published:
        leaderboard_url = reverse(
            "evaluation:leaderboard",
            kwargs={
                "challenge_short_name": challenge.short_name,
                "slug": evaluation.submission.phase.slug,
            },
        )
        message += (
            f"You can view the result on the leaderboard here: "
            f"{leaderboard_url}"
        )
        recipients.append(evaluation.submission.creator)
    else:
        message += (
            f"You can publish the result on the leaderboard here: "
            f"{evaluation.get_absolute_url()}"
        )
    message += (
        f"\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )
    for recipient in recipients:
        send_mail(
            subject=(
                f"[{site.domain.lower()}] "
                f"[{challenge.short_name.lower()}] "
                f"New Result"
            ),
            message=message.format(recipient.username),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
        )
