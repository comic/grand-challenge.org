from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.html import format_html

from grandchallenge.subdomains.utils import reverse


def send_challenge_requested_email_to_reviewers(challengerequest):
    site = Site.objects.get_current()
    update_url = reverse(
        "challenges:requests-list",
    )
    message = format_html(
        "Dear reviewers,\n\n"
        "User {user} has just requested the challenge "
        "{request_title}. To review the challenge, go here: {update_url}\n\n"
        "Regards,\n{site_name}\n\n"
        "This is an automated service email from {site_domain}.",
        user=challengerequest.creator,
        request_title=challengerequest.title,
        update_url=update_url,
        site_name=site.name,
        site_domain=site.domain,
    )
    reviewers = get_user_model().objects.filter(
        Q(groups__permissions__codename="change_challengerequest")
        | Q(user_permissions__codename="change_challengerequest")
    )
    send_mail(
        subject=f"[{site.domain.lower()}] New Challenge Requested",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email for user in reviewers],
    )


def send_challenge_requested_email_to_requester(challengerequest):
    site = Site.objects.get_current()
    link = reverse("challenges:requests-list")
    budget = ""
    for key, value in challengerequest.budget.items():
        budget += f"{key}: {value} €\n"
    context = {
        "username": challengerequest.creator.username,
        "site_name": site.name,
        "domain": site.domain,
        "budget": budget,
        "link": link,
    }
    message = render_to_string(
        "challenges/partials/challenge_request_confirmation_email.txt", context
    )
    send_mail(
        subject=f"[{site.domain.lower()}] [{challengerequest.short_name}] Challenge Request Submitted Successfully",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[challengerequest.creator.email],
    )


def send_challenge_status_update_email(challengerequest, challenge=None):
    site = Site.objects.get_current()
    message = ""
    context = {
        "username": challengerequest.creator.username,
        "site_name": site.name,
        "domain": site.domain,
    }
    if (
        challengerequest.status
        == challengerequest.ChallengeRequestStatusChoices.ACCEPTED
    ):
        context.update({"challenge_link": challenge.get_absolute_url()})
        message = render_to_string(
            "challenges/partials/challenge_request_acceptance_email.txt",
            context,
        )
    elif (
        challengerequest.status
        == challengerequest.ChallengeRequestStatusChoices.REJECTED
    ):
        message = render_to_string(
            "challenges/partials/challenge_request_rejection_email.txt",
            context,
        )

    send_mail(
        subject=f"[{site.domain.lower()}] [{challengerequest.short_name}] Challenge Request Update",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[challengerequest.creator.email],
    )
