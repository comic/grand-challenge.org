from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.utils.html import format_html

from grandchallenge.subdomains.utils import reverse


def send_failed_evaluation_email(evaluation):
    site = Site.objects.get_current()
    recipients = list(evaluation.submission.phase.challenge.get_admins())
    recipients.append(evaluation.submission.creator)
    for recipient in recipients:
        message = format_html(
            "Dear {recipient},\n\n"
            "Unfortunately the evaluation for the submission to {challenge} "
            "failed with an error. The error message is:\n\n"
            "{error_message}\n\n"
            "You may wish to try and correct this, or contact the challenge "
            "organizers. The following information may help them:\n"
            "User: {user}\n"
            "Evaluation ID: {evaluation_id}\n"
            "Submission ID: {submission_id}\n\n"
            "Regards,\n"
            "{site}\n\n"
            "This is an automated service email from {domain}",
            recipient=recipient.username,
            challenge=evaluation.submission.phase.challenge.short_name,
            error_message=evaluation.error_message,
            user=evaluation.submission.creator.username,
            evaluation_id=evaluation.pk,
            submission_id=evaluation.submission.pk,
            site=site.name,
            domain=site.domain,
        )
        send_mail(
            subject=(
                f"[{site.domain.lower()}] "
                f"[{evaluation.submission.phase.challenge.short_name.lower()}] "
                f"Evaluation Failed"
            ),
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
        )


def send_successful_evaluation_email(evaluation):
    site = Site.objects.get_current()
    challenge = evaluation.submission.phase.challenge

    recipients = list(challenge.get_admins())

    if evaluation.published:
        recipients.append(evaluation.submission.creator)

    for recipient in recipients:
        message = format_html(
            "Dear {recipient},\n\n"
            "There is a new result for {challenge} from {user}.",
            recipient=recipient.username,
            challenge=challenge.short_name,
            user=evaluation.submission.creator.username,
        )
        if evaluation.published:
            leaderboard_url = reverse(
                "evaluation:leaderboard",
                kwargs={
                    "challenge_short_name": challenge.short_name,
                    "slug": evaluation.submission.phase.slug,
                },
            )
            message += format_html(
                "You can view the result on the leaderboard here: {leaderboard}\n\n",
                leaderboard=leaderboard_url,
            )
        else:
            message += format_html(
                "You can publish the result on the leaderboard here: {leaderboard}\n\n",
                leaderboard=evaluation.get_absolute_url(),
            )
        message += format_html(
            "Regards,\n"
            "{site}\n\n"
            "This is an automated service email from {domain}",
            site=site.name,
            domain=site.domain,
        )
        send_mail(
            subject=(
                f"[{site.domain.lower()}] "
                f"[{challenge.short_name.lower()}] "
                f"New Result"
            ),
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
        )


def send_missing_method_email(submission):
    site = Site.objects.get_current()
    challenge = submission.phase.challenge

    recipients = challenge.get_admins()

    for recipient in recipients:
        message = format_html(
            "Dear {recipient},\n\n"
            "The submission from {user} could not be evaluated, "
            "because there is no valid evaluation method for {challenge} in the {phase} evaluation phase. "
            "Please upload an evaluation method container.\n\n"
            "Regards,\n"
            "{site}\n\n"
            "This is an automated service email from {domain}.",
            recipient=recipient.username,
            user=submission.creator.username,
            challenge=challenge.short_name,
            phase=submission.phase.slug,
            site=site.name,
            domain=site.domain,
        )
        send_mail(
            subject=(
                f"[{site.domain.lower()}] "
                f"[{challenge.short_name.lower()}] "
                f"No evaluation method"
            ),
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
        )
