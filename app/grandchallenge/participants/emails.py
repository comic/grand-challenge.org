from django.contrib.sites.shortcuts import get_current_site

from grandchallenge.core.utils.email import send_templated_email


def send_participation_request_notification_email(request, obj):
    """ When a user requests to become a participant, let this know to all admins

    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user requested
                 participation for which project

    """
    title = f"[{obj.challenge.short_name.lower()}] New Participation Request"
    mainportal = get_current_site(request)
    kwargs = {"user": obj.user, "site": mainportal, "challenge": obj.challenge}
    for admin in obj.challenge.get_admins():
        kwargs["admin"] = admin
        send_templated_email(
            title,
            "participants/emails/participation_request_notification_email.html",
            kwargs,
            [admin.email],
            request=request,
        )


def send_participation_request_accepted_email(request, obj):
    """ When a users requests to become a participant is accepted, let the user know

    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user requested
                 participation for which project

    """
    title = (
        f"[{obj.challenge.short_name.lower()}] Participation Request Accepted"
    )
    mainportal = get_current_site(request)
    kwargs = {
        "user": obj.user,
        "adder": request.user,
        "site": mainportal,
        "challenge": obj.challenge,
    }
    send_templated_email(
        title,
        "participants/emails/participation_request_accepted_email.html",
        kwargs,
        [obj.user.email],
        request=request,
    )


def send_participation_request_rejected_email(request, obj):
    """ When a users requests to become a participant is rejected, let the user know

    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user requested
                 participation for which project

    """
    title = (
        f"[{obj.challenge.short_name.lower()}] Participation Request Rejected"
    )
    mainportal = get_current_site(request)
    kwargs = {
        "user": obj.user,
        "adder": request.user,
        "site": mainportal,
        "challenge": obj.challenge,
    }
    send_templated_email(
        title,
        "participants/emails/participation_request_rejected_email.html",
        kwargs,
        [obj.user.email],
        request=request,
    )
