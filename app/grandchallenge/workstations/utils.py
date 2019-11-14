from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404

from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)


def get_or_create_active_session(
    *, user, workstation_image: WorkstationImage
) -> Session:
    """
    Queries the database to see if there is an active session for this user and
    workstation image, if not, it will create one.

    Parameters
    ----------
    user
        The creator of the session
    workstation_image
        The workstation image for the session

    Returns
    -------
        An active session for this user and workstation image.

    """
    session = (
        Session.objects.filter(
            creator=user,
            status__in=[Session.QUEUED, Session.STARTED, Session.RUNNING],
            workstation_image=workstation_image,
        )
        .order_by("-created")
        .first()
    )

    if session is None:
        session = Session.objects.create(
            creator=user, workstation_image=workstation_image
        )

    return session


def get_workstation_image_or_404(
    *, pk: str = None, slug: str = settings.DEFAULT_WORKSTATION_SLUG
) -> WorkstationImage:
    """
    Gets the workstation image based on the provided pk. If this is absent,
    gets the workstation from the slug and returns the latest container image
    for this workstation.

    Parameters
    ----------
    pk
        The primary key of the workstation image
    slug
        The slug of the workstation

    Raises
    ------
    Http404
        If either the Workstation or WorkstationImage cannot be found

    Returns
    -------
        The `WorkstationImage` that corresponds to this `pk` or `slug`.
    """
    if pk is not None:
        workstation_image = get_object_or_404(WorkstationImage, pk=pk)
    else:
        workstation = get_object_or_404(Workstation, slug=slug)

        workstation_image = workstation.latest_ready_image
        if workstation_image is None:
            raise Http404("No container images found for this workstation")

    return workstation_image
