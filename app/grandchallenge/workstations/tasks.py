from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task

from grandchallenge.components.backends.amazon_ecs import ECSTaskOrchestrator


@lambda_task
def consolidate_unclaimed_sessions():
    from grandchallenge.workstations.models import Session, Workstation

    workstation = Workstation.objects.get(
        slug=settings.DEFAULT_WORKSTATION_SLUG
    )
    workstation_image = workstation.active_image

    if workstation_image is None:
        return {"n_sessions_stopped": 0, "n_sessions_started": 0}

    unclaimed_sessions = (
        Session.objects.active()
        .select_for_update(skip_locked=True)
        .filter(claimed_at=None)
    )

    expiring_pks = set()

    for session in unclaimed_sessions:
        task_expired = session.created < now() - timedelta(
            hours=settings.WORKSTATIONS_MAXIMUM_UNCLAIMED_SESSION_HOURS
        )

        task_uses_old_image = session.workstation_image != workstation_image

        if (
            task_expired
            or task_uses_old_image
            or _is_session_stopped_on_ecs(session=session)
        ):
            expiring_pks.add(session.pk)
            session.status = Session.EXPIRED
            session.save()

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
        "n_sessions_stopped": len(expiring_pks),
        "n_sessions_started": n_sessions_started,
    }


def _is_session_stopped_on_ecs(*, session):
    if session.task_arn:
        orchestrator = ECSTaskOrchestrator(**session.orchestrator_kwargs)

        try:
            task_description = orchestrator.get_task_description(
                task_arn=session.task_arn
            )
        except ObjectDoesNotExist:
            # The task_arn was created but no longer exists, so must have stopped
            return True

        # Status options from https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle-explanation.html
        return task_description["lastStatus"] in {
            "DEACTIVATING",
            "STOPPING",
            "DEPROVISIONING",
            "STOPPED",
            "DELETED",
        }
    else:
        # No task_arn, so nothing could have stopped
        return False
