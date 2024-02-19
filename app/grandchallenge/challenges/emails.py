from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.subdomains.utils import reverse


def send_challenge_requested_email_to_reviewers(challengerequest):
    update_url = reverse(
        "challenges:requests-list",
    )
    message = format_html(
        "<p>User {user} has just requested the challenge "
        "{request_title}. To review the challenge, "
        "go here: <a href='{update_url}'>{update_url}</a></p>",
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
    send_standard_email_batch(
        subject="New Challenge Requested",
        message=message,
        recipients=reviewers,
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
    send_standard_email_batch(
        subject=format_html(
            "[{request_title}] Challenge Request Submitted Successfully",
            request_title=challengerequest.short_name,
        ),
        message=message,
        recipients=[challengerequest.creator],
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

    send_standard_email_batch(
        subject=format_html(
            "[{request_title}] Challenge Request Update",
            request_title=challengerequest.short_name,
        ),
        message=message,
        recipients=[challengerequest.creator],
    )
