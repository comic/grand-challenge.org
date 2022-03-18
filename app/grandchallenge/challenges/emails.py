from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import mail_managers, send_mail
from django.db.models import Q
from django.utils.html import format_html

from grandchallenge.subdomains.utils import reverse


def send_external_challenge_created_email(challenge):
    site = Site.objects.get_current()
    update_url = reverse(
        "challenges:external-update",
        kwargs={"short_name": challenge.short_name},
    )

    message = format_html(
        "Dear manager,\n\n"
        "User {user} has just created the challenge {challenge_short_name}. "
        "You need to un-hide it "
        "before it is visible on the all challenges page, you can do that "
        "here: {update_url}\n\n"
        "Regards,\n{site_name}\n\n"
        "This is an automated service email from {site_domain}.",
        user=challenge.creator,
        challenge_short_name=challenge.short_name,
        update_url=update_url,
        site_name=site.name,
        site_domain=site.domain,
    )

    mail_managers(
        subject=f"[{site.domain.lower()}] New External Challenge",
        message=message,
    )


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
    addition = ""
    if (
        challengerequest.challenge_type
        == challengerequest.ChallengeTypeChoices.T2
    ):
        budget = ""
        for key, value in challengerequest.budget.items():
            budget += f"{key}: {value}\n"
        addition += (
            f"For your type 2 challenge, we have calculated the following "
            f"budget estimate. This estimate is based on the information "
            f"you provided in the form and reflects a rough estimation of"
            f"the costs we expect to incurr:\n"
            f"{budget}\n\n"
        )

    message = format_html(
        "Dear {user},\n\n"
        "Your challenge request has been sent to the reviewers. You will "
        "receive an email informing you of our decision within the next 4 weeks. "
        "The reviewers might contact you for additional information during "
        "that time.\n"
        "{addition}"
        "Regards,\n"
        "{site_name} team\n\n"
        "This is an automated service email from {site_domain}.",
        user=challengerequest.creator.username,
        addition=addition,
        site_name=site.name,
        site_domain=site.domain,
    )

    send_mail(
        subject=f"[{site.domain.lower()}] Challenge Request Submitted Successfully",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[challengerequest.creator.email],
    )


def send_challenge_status_update_email(challengerequest, challenge=None):
    site = Site.objects.get_current()
    message = ""
    if (
        challengerequest.status
        == challengerequest.ChallengeRequestStatusChoices.ACCEPTED
    ):
        message = format_html(
            "Dear {},\n\n"
            "We are happy to inform you that your challenge request has been "
            "accepted. For your convenience, we have already created the "
            "challenge page for you at {} "
            "Note that your challenge is currently hidden and is not yet "
            "listed on our challenge overview page. Once your challenge is "
            "all set-up, you can make it public by going to Admin - General "
            "Settings and unchecking the 'hidden' box. \n"
            "To get your challenge ready, please have a close look at our "
            "documentation (https://grand-challenge.org/documentation/"
            "create-your-own-challenge/) and the steps below. \n\n"
            "Next steps:\n"
            "1. On your challenge page, go to Admin - General Settings and "
            "carefully review all information there, upload a logo and banner for"
            "your challenge, optionally enable the forum (recommended) and "
            "teams features and choose your preferred access request handling "
            "policy. All these options are described in our documentation.\n"
            "2. Add information about your challenge, your submission procedure, "
            "the challenge timeline etc to your challenge page by editing and "
            "adding custom subpages to your challenge. For more information, "
            "see the tab 'Add custom pages' in our documentation.\n"
            "3. A first phase has been added to your challenge, to add more go "
            "to Admin - Phases - Add a new Phase. Please carefully read our "
            "documentation for details on how to set up your phases for a type 1"
            "or a type 2 challenge respectively. \n\n"
            "Feel free to contact support@grand-challenge.org if you have any "
            "questions or require assistance in setting up your challenge. \n"
            "Thank you for choosing Grand Challenge. We are looking forward to "
            "hosting your challenge. \n\n"
            "Regards,\n"
            "{} team\n\n"
            "This is an automated service email from {}.",
            challengerequest.creator.username,
            challenge.get_absolute_url(),
            site.name,
            site.domain,
        )
    elif (
        challengerequest.status
        == challengerequest.ChallengeRequestStatusChoices.REJECTED
    ):
        message = format_html(
            "Dear {user},\n\n"
            "We are very sorry to have to inform you that we will not be able to "
            "host your challenge on our platform. We can only support a limited "
            "number of challenges per year and hence have to be selective in "
            "reviewing proposals. We would like to nevertheless thank you for "
            "your submission and wish you the best of luck with organizing and "
            "hosting your challenge elsewhere.\n\n"
            "Regards,\n"
            "{site_name} team\n\n"
            "This is an automated service email from {site_domain}.",
            user=challengerequest.creator.username,
            site_name=site.name,
            site_domain=site.domain,
        )

    send_mail(
        subject=f"[{site.domain.lower()}] Challenge Request Update",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[challengerequest.creator.email],
    )
