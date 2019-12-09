from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from grandchallenge.evaluation.templatetags.evaluation_extras import user_error
from grandchallenge.subdomains.utils import reverse


def send_failed_job_email(job):
    site = Site.objects.get_current()
    message = (
        f"Dear {{}},\n\n"
        f"Unfortunately the evaluation for the submission to "
        f"{job.submission.challenge.short_name} failed with an error. "
        f"The error message is:\n\n"
        f"{user_error(job.output)}\n\n"
        f"You may wish to try and correct this, or contact the challenge "
        f"organizers. The following information may help them:\n"
        f"User: {job.submission.creator.username}\n"
        f"Job ID: {job.pk}\n"
        f"Submission ID: {job.submission.pk}\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )
    recipients = list(job.submission.challenge.get_admins())
    recipients.append(job.submission.creator)
    for recipient in recipients:
        send_mail(
            subject=(
                f"[{site.domain.lower()}] "
                f"[{job.submission.challenge.short_name.lower()}] "
                f"Evaluation Failed"
            ),
            message=message.format(recipient.username),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
        )


def send_new_result_email(result):
    site = Site.objects.get_current()
    challenge = result.job.submission.challenge

    recipients = list(challenge.get_admins())
    message = (
        f"Dear {{}},\n\n"
        f"There is a new result for {challenge.short_name} from "
        f"{result.job.submission.creator.username}. "
    )
    if result.published:
        leaderboard_url = reverse(
            "evaluation:result-list",
            kwargs={"challenge_short_name": challenge.short_name},
        )
        message += (
            f"You can view the result on the leaderboard here: "
            f"{leaderboard_url}"
        )
        recipients.append(result.job.submission.creator)
    else:
        message += (
            f"You can publish the result on the leaderboard here: "
            f"{result.get_absolute_url()}"
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
