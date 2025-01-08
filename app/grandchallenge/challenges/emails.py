from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import mail_managers
from django.template.loader import render_to_string
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import EmailSubscriptionTypes
from grandchallenge.subdomains.utils import reverse


def send_challenge_requested_email_to_reviewers(challengerequest):
    update_url = reverse(
        "challenges:requests-list",
    )
    message = format_html(
        "User {user} has just requested the challenge "
        "{request_title}. To review the challenge, "
        "go [here]({update_url}).",
        user=challengerequest.creator,
        request_title=challengerequest.title,
        update_url=update_url,
    )
    reviewers = (
        get_user_model()
        .objects.filter(
            groups__permissions__codename="change_challengerequest"
        )
        .distinct()
    )
    site = Site.objects.get_current()
    send_standard_email_batch(
        site=site,
        subject="New Challenge Requested",
        markdown_message=message,
        recipients=reviewers,
        subscription_type=EmailSubscriptionTypes.SYSTEM,
    )


def send_challenge_requested_email_to_requester(challengerequest):
    link = reverse("challenges:requests-list")

    context = {
        "link": link,
    }
    message = render_to_string(
        "challenges/partials/challenge_request_confirmation_email.md",
        context,
    )
    site = Site.objects.get_current()
    send_standard_email_batch(
        site=site,
        subject=format_html(
            "[{request_title}] Challenge Request Submitted Successfully",
            request_title=challengerequest.short_name,
        ),
        markdown_message=message,
        recipients=[challengerequest.creator],
        subscription_type=EmailSubscriptionTypes.SYSTEM,
    )


def send_challenge_status_update_email(challengerequest, challenge=None):
    message = ""
    context = {}
    if (
        challengerequest.status
        == challengerequest.ChallengeRequestStatusChoices.ACCEPTED
    ):
        context.update({"challenge_link": challenge.get_absolute_url()})
        message = render_to_string(
            "challenges/partials/challenge_request_acceptance_email.md",
            context,
        )
    elif (
        challengerequest.status
        == challengerequest.ChallengeRequestStatusChoices.REJECTED
    ):
        message = render_to_string(
            "challenges/partials/challenge_request_rejection_email.md",
            context,
        )
    site = Site.objects.get_current()
    send_standard_email_batch(
        site=site,
        subject=format_html(
            "[{request_title}] Challenge Request Update",
            request_title=challengerequest.short_name,
        ),
        markdown_message=message,
        recipients=[challengerequest.creator],
        subscription_type=EmailSubscriptionTypes.SYSTEM,
    )


def send_email_percent_budget_consumed_alert(challenge, percent_threshold):
    subject = format_html(
        "[{challenge_name}] over {percent_threshold}% Budget Consumed Alert",
        challenge_name=challenge.short_name,
        percent_threshold=percent_threshold,
    )
    message = format_html(
        "We would like to inform you that more than {percent_threshold}% of the "
        "compute budget for the {challenge_name} challenge has been used. "
        "You can find an overview of the costs [here]({statistics_url}).",
        challenge_name=challenge.short_name,
        percent_threshold=percent_threshold,
        statistics_url=reverse(
            "pages:statistics",
            kwargs={"challenge_short_name": challenge.short_name},
        ),
    )
    send_standard_email_batch(
        site=Site.objects.get_current(),
        subject=subject,
        markdown_message=message,
        recipients=[*challenge.get_admins()],
        subscription_type=EmailSubscriptionTypes.SYSTEM,
    )
    mail_managers(
        subject=subject,
        message=message,
    )
