from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
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
    budget = {}
    for key, value in challengerequest.budget.items():
        budget[key] = value
    context = {
        "budget": budget,
        "link": link,
    }
    message = render_to_string(
        "challenges/partials/challenge_request_confirmation_email.html",
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
            "challenges/partials/challenge_request_acceptance_email.html",
            context,
        )
    elif (
        challengerequest.status
        == challengerequest.ChallengeRequestStatusChoices.REJECTED
    ):
        message = render_to_string(
            "challenges/partials/challenge_request_rejection_email.html",
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
