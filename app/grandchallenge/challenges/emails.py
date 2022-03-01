from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.mail import mail_managers, send_mail

from config import settings
from grandchallenge.subdomains.utils import reverse


def send_challenge_created_email(challenge):
    site = Site.objects.get_current()
    message = (
        f"Dear manager,\n\n"
        f"User {challenge.creator} has just created the challenge "
        f"{challenge.short_name} at {challenge.get_absolute_url()}.\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    mail_managers(
        subject=f"[{site.domain.lower()}] New Challenge Created",
        message=message,
    )


def send_external_challenge_created_email(challenge):
    site = Site.objects.get_current()
    update_url = reverse(
        "challenges:external-update",
        kwargs={"short_name": challenge.short_name},
    )

    message = (
        f"Dear manager,\n\n"
        f"User {challenge.creator} has just created the challenge "
        f"{challenge.short_name}. You need to un-hide it before it is visible "
        f"on the all challenges page, you can do that here: {update_url}\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )

    mail_managers(
        subject=f"[{site.domain.lower()}] New External Challenge",
        message=message,
    )


def send_challenge_requested_email_to_reviewers(challengerequest):
    site = Site.objects.get_current()
    message = (
        f"Dear reviewers,\n\n"
        f"User {challengerequest.creator} has just requested the challenge "
        f"{challengerequest.title}.\n\n"
        f"Regards,\n"
        f"{site.name}\n\n"
        f"This is an automated service email from {site.domain}."
    )
    reviewers = (
        Group.objects.filter(name=settings.CHALLENGE_REVIEWERS_GROUP_NAME)
        .get()
        .user_set.all()
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
            f"For your type 2 challenge, we have calculated the following budget estimate "
            f"based on the information you provided:\n"
            f"{budget}\n\n"
        )

    message = (
        f"Dear {challengerequest.creator.username},\n\n"
        f"Your challenge request has been sent to the reviewers. You will "
        f"receive an email informing you of our decision within the next 4 weeks. "
        f"The reviewers might contact you for additional information during "
        f"that time.\n"
        f"{addition}"
        f"Regards,\n"
        f"{site.name} team\n\n"
        f"This is an automated service email from {site.domain}."
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
        message = (
            f"Dear {challengerequest.creator.username},\n\n"
            f"We are happy to inform you that your challenge request has been "
            f"accepted. For your convenience, we have already created the "
            f"challenge page for you at {challenge.get_absolute_url()} "
            f"To get your challenge ready, please have a close look at our "
            f"documentation: \n\n"
            f"Next steps:\n"
            f"1. On your challenge page, go to Admin - General Settings and carefully "
            f"review all information there, upload a logo and banner for your "
            f"challenge, optionally enable the forum (recommended) and teams features "
            f"and choose your preferred access request handling policy. For more "
            f"information, see here.\n"
            f"2. Add information about your challenge, your submission procedure, "
            f"the challenge timeline etc to your challenge page by editing and adding"
            f" custom subpages to your challenge. For more information, see here.\n"
            f"3. A first phase has been added to your challenge, to add more go "
            f"to Admin - Phases - Add a new Phase. Please carefully read our "
            f"documentation for details on how to set up your phases for a type 1 "
            f"or a type 2 challenge respectively. \n\n"
            f"Feel free to contact support@grand-challenge.org if you have any "
            f"questions or require assistance in setting up your challenge. \n"
            f"Thank you for choosing Grand Challenge. We are looking forward to "
            f"hosting your challenge. \n\n"
            f"Regards,\n"
            f"{site.name} team\n\n"
            f"This is an automated service email from {site.domain}."
        )
    elif (
        challengerequest.status
        == challengerequest.ChallengeRequestStatusChoices.REJECTED
    ):
        message = (
            f"Dear {challengerequest.creator.username},\n\n"
            "We are very sorry to have to inform you that we will not be able to "
            "host your challenge on our platform. We can only support a limited "
            "number of challenges per year and hence have to be selective in "
            "reviewing proposals. We would like to nevertheless thank you for your"
            "submission and wish you the best of luck with organizing and hosting "
            "your challenge elsewhere.\n\n"
            f"Regards,\n"
            f"{site.name} team\n\n"
            f"This is an automated service email from {site.domain}."
        )

    send_mail(
        subject=f"[{site.domain.lower()}] Challenge Request Update",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[challengerequest.creator.email],
    )
