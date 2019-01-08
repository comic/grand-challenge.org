from django.conf import settings
from django.core.mail import send_mail

from grandchallenge.subdomains.utils import reverse
from grandchallenge.evaluation.templatetags.evaluation_extras import user_error


def send_failed_job_email(job):
    message = (
        f"Unfortunately the evaluation for the submission to "
        f"{job.challenge.short_name} failed with an error. The error message "
        f"is:\n\n"
        f"{user_error(job.output)}\n\n"
        f"You may wish to try and correct this, or contact the challenge "
        f"organizers. The following information may help them:\n"
        f"User: {job.submission.creator.username}\n"
        f"Job ID: {job.pk}\n"
        f"Submission ID: {job.submission.pk}"
    )
    recipient_emails = [o.email for o in job.challenge.get_admins()]
    recipient_emails.append(job.submission.creator.email)
    for email in recipient_emails:
        send_mail(
            subject="Evaluation Failed",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )


def send_new_result_email(result):
    recipient_emails = [o.email for o in result.challenge.get_admins()]
    message = (
        f"There is a new result for {result.challenge.short_name} from "
        f"{result.job.submission.creator.username}."
    )
    if result.published:
        leaderboard_url = reverse(
            "evaluation:result-list",
            kwargs={"challenge_short_name": result.challenge.short_name},
        )
        message += (
            f"You can view the result on the leaderboard here: "
            f"{leaderboard_url}"
        )
        recipient_emails.append(result.job.submission.creator.email)
    else:
        message += (
            f"You can publish the result on the leaderboard here: "
            f"{result.get_absolute_url()}"
        )
    for email in recipient_emails:
        send_mail(
            subject=f"New Result for {result.challenge.short_name}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
