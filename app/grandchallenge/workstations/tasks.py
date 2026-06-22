from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task

from grandchallenge.components.tasks import stop_service


@lambda_task
def consolidate_unclaimed_sessions():
    from grandchallenge.workstations.models import Session, Workstation

    workstation = Workstation.objects.get(
        slug=settings.DEFAULT_WORKSTATION_SLUG
    )
    workstation_image = workstation.active_image

    if workstation_image is None:
        return {"n_sessions_stopped": 0, "n_sessions_started": 0}

    sessions_to_stop = list(
        Session.objects.active()
        .select_for_update(skip_locked=True)
        .filter(claimed_at=None)
        .filter(
            Q(
                created__lt=now()
                - timedelta(
                    hours=settings.WORKSTATIONS_MAXIMUM_UNCLAIMED_SESSION_HOURS
                )
            )
            | ~Q(workstation_image=workstation_image)
        )
    )

    expiring_pks = {session.pk for session in sessions_to_stop}

    for session in sessions_to_stop:
        stop_service.execute_on_commit(**session.task_kwargs)

    n_sessions_started = 0

    for region in settings.WORKSTATIONS_ACTIVE_REGIONS:
        active_regional_sessions = (
            Session.objects.active()
            .filter(region=region)
            .exclude(pk__in=expiring_pks)
        )
        active_unclaimed_sessions = (
            Session.objects.active()
            .filter(
                claimed_at=None,
                region=region,
                workstation_image=workstation_image,
            )
            .exclude(pk__in=expiring_pks)
        )

        n_sessions_to_start = min(
            max(
                0,
                settings.WORKSTATIONS_NUMBER_UNCLAIMED_SESSIONS
                - active_unclaimed_sessions.count(),
            ),
            max(
                0,
                settings.WORKSTATIONS_MAXIMUM_SESSIONS
                - active_regional_sessions.count(),
            ),
        )

        for _ in range(n_sessions_to_start):
            Session.objects.create(
                workstation_image=workstation_image,
                region=region,
            )
            n_sessions_started += 1

    return {
        "n_sessions_stopped": len(sessions_to_stop),
        "n_sessions_started": n_sessions_started,
    }
