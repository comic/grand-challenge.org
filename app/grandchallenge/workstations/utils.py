from django.contrib.auth.models import Permission

from grandchallenge.workstations.models import (
    Session,
    WorkstationGroupObjectPermission,
    WorkstationImage,
)


def get_or_create_active_session(
    *,
    user,
    workstation_image: WorkstationImage,
    region: str,
    ping_times=None,
    extra_env_vars=None,
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
            region=region,
        )
        .order_by("-created")
        .first()
    )

    if session is None:
        session = Session.objects.create(
            creator=user,
            workstation_image=workstation_image,
            region=region,
            # Ping times and env vars are only set for new Sessions
            ping_times=ping_times or None,
            extra_env_vars=extra_env_vars or [],
        )

    return session


def reassign_workstation_permissions(*, groups, workstation):
    """
    Removes all permissions for the given groups to view workstations
    and assigns them to the new one if provided
    """
    permission = Permission.objects.get(
        content_type__app_label="workstations",
        codename="view_workstation",
    )

    WorkstationGroupObjectPermission.objects.filter(
        permission=permission, group__in=groups
    ).delete()

    if workstation:
        for group in groups:
            WorkstationGroupObjectPermission.objects.create(
                content_object=workstation,
                group=group,
                permission=permission,
            )
