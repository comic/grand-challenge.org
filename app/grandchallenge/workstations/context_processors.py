from grandchallenge.workstations.models import Session


def workstation_session(request):
    """ Adds workstation_session. request.user must be set """
    return {
        "workstation_session": (
            Session.objects.filter(creator=request.user)
            .exclude(status__in=[Session.QUEUED, Session.STOPPED])
            .order_by("-created")
            .select_related("workstation_image__workstation")
            .first()
        )
    }
