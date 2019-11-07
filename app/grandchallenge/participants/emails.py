from grandchallenge.core.utils.email import send_templated_email


def send_participation_request_notification_email(request, obj):
    """
    Email the challenge admins when a new participant request is created.

    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user
                 requested participation for which challenge
    """
    title = f"[{obj.challenge.short_name.lower()}] New Participation Request"
    kwargs = {
        "user": obj.user,
        "site": request.site,
        "challenge": obj.challenge,
    }
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
    """
    Email the user when a participant request is accepted.

    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user
                 requested participation for which challenge
    """
    title = (
        f"[{obj.challenge.short_name.lower()}] Participation Request Accepted"
    )
    kwargs = {
        "user": obj.user,
        "adder": request.user,
        "site": request.site,
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
    """
    Email the user when a participation request is rejected.

    request:     HTTPRequest containing the current admin posting this
    obj:         ParticipationRequest object containing info on which user
                 requested participation for which challenge
    """
    title = (
        f"[{obj.challenge.short_name.lower()}] Participation Request Rejected"
    )
    kwargs = {
        "user": obj.user,
        "adder": request.user,
        "site": request.site,
        "challenge": obj.challenge,
    }
    send_templated_email(
        title,
        "participants/emails/participation_request_rejected_email.html",
        kwargs,
        [obj.user.email],
        request=request,
    )
