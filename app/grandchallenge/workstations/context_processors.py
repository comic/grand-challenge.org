from grandchallenge.workstations.models import Session


def workstation_session(request):
    """ Adds workstation_session. request.user must be set """

    s = None

    if not request.user.is_anonymous:
        s = (
            Session.objects.filter(creator=request.user)
            .exclude(status__in=[Session.QUEUED, Session.STOPPED])
            .order_by("-created")
            .select_related("workstation_image__workstation")
            .first()
        )

    return {"workstation_session": s}
