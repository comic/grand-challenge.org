import math
from typing import NamedTuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, F, Max, Min, Q
from django.utils.timezone import datetime, now
from lambda_tasks.decorators import lambda_task
from lambda_tasks.settings import MAX_DELAY

from grandchallenge.challenges.costs import (
    annotate_invoice_compute_costs,
    annotate_job_duration_and_compute_costs,
    annotate_storage_size,
)
from grandchallenge.challenges.emails import (
    send_challenge_requests_draft_reminder,
    send_onboarding_task_due_reminder,
    send_onboarding_task_overdue_alert,
    send_onboarding_task_support_overdue_alert,
)
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    OnboardingTask,
)
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.utils.query import check_lock_acquired
from grandchallenge.evaluation.models import Evaluation, Phase
from grandchallenge.invoices.models import Invoice


@lambda_task
def update_challenge_results_cache():
    challenges = Challenge.objects.all()
    evaluation_info = (
        Evaluation.objects.filter(published=True, rank__gt=0)
        .values("submission__phase__challenge_id")
        .annotate(
            cached_num_results=Count("submission__phase__challenge_id"),
            cached_latest_result=Max("created"),
        )
    )
    evaluation_info_by_challenge = {
        str(v["submission__phase__challenge_id"]): v for v in evaluation_info
    }
    participant_counts = (
        get_user_model()
        .objects.values("groups__participants_of_challenge")
        .annotate(cached_num_participants=Count("pk"))
    )
    participant_counts_by_challenge = {
        str(v["groups__participants_of_challenge"]): v
        for v in participant_counts
    }

    for c in challenges:
        c.cached_num_results = evaluation_info_by_challenge.get(
            str(c.pk), {}
        ).get("cached_num_results", 0)
        c.cached_latest_result = evaluation_info_by_challenge.get(
            str(c.pk), {}
        ).get("cached_latest_result", None)
        c.cached_num_participants = participant_counts_by_challenge.get(
            str(c.pk), {}
        ).get("cached_num_participants", 0)

    Challenge.objects.bulk_update(
        challenges,
        [
            "cached_num_results",
            "cached_num_participants",
            "cached_latest_result",
        ],
    )


@lambda_task
def update_challenge_compute_costs():
    seconds_per_task = math.ceil(MAX_DELAY / max(Challenge.objects.count(), 1))

    for idx, challenge in enumerate(Challenge.objects.only("pk")):
        update_challenge_compute_cost.execute_on_commit(
            pk=challenge.pk,
            _delay=(idx * seconds_per_task) % MAX_DELAY,
        )


@lambda_task(retry_on=(LockNotAcquiredException,))
def update_challenge_compute_cost(*, pk: int):
    with check_lock_acquired():
        invoices = list(
            Invoice.objects.select_for_update(nowait=True, of=("self",))
            .filter(challenge_id=pk)
            .with_budget_authorization()
        )
        phases = list(
            Phase.objects.select_for_update(nowait=True, of=("self",)).filter(
                challenge_id=pk
            )
        )

    for invoice in invoices:
        annotate_invoice_compute_costs(invoice=invoice)
        invoice.save(update_fields=("compute_cost_euro_millicents",))

    for phase in phases:
        annotate_job_duration_and_compute_costs(phase=phase)
        phase.save(
            skip_calculate_ranks=True,
            update_fields=(
                "average_algorithm_job_duration",
                "compute_cost_euro_millicents",
            ),
        )


@lambda_task
def update_challenge_storage_sizes():
    seconds_per_task = math.ceil(MAX_DELAY / max(Challenge.objects.count(), 1))

    for idx, challenge in enumerate(Challenge.objects.only("pk")):
        update_challenge_storage_size.execute_on_commit(
            pk=challenge.pk,
            _delay=(idx * seconds_per_task) % MAX_DELAY,
        )


@lambda_task
def update_challenge_storage_size(*, pk: int):
    challenge = Challenge.objects.get(pk=pk)
    annotate_storage_size(challenge=challenge)
    challenge.save(
        update_fields=(
            "size_in_storage",
            "size_in_registry",
        )
    )


class OnboardingTaskInfo(NamedTuple):
    challenge: str
    num_is_overdue: int
    num_is_overdue_soon: int
    min_deadline: datetime
    num_support_is_overdue: int
    min_support_deadline: datetime


@lambda_task
def send_onboarding_task_reminder_emails():
    onboarding_task_info = (
        OnboardingTask.objects.with_overdue_status()
        .values("challenge")
        .annotate(
            num_is_overdue=Count(
                "pk",
                filter=Q(
                    is_overdue=True,
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                ),
            ),
            num_is_overdue_soon=Count(
                "pk",
                filter=Q(
                    is_overdue_soon=True,
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                ),
            ),
            min_deadline=Min(
                "deadline",
                filter=Q(
                    is_overdue=True,
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                ),
            ),
            num_support_is_overdue=Count(
                "pk",
                filter=Q(
                    is_overdue=True,
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
                ),
            ),
            min_support_deadline=Min(
                "deadline",
                filter=Q(
                    is_overdue=True,
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
                ),
            ),
        )
        .exclude(
            num_is_overdue=0,
            num_is_overdue_soon=0,
            num_support_is_overdue=0,
        )
    )

    onboarding_task_info_by_challenge = {
        str(v["challenge"]): OnboardingTaskInfo(**v)
        for v in onboarding_task_info
    }

    challenges = Challenge.objects.filter(
        pk__in=onboarding_task_info_by_challenge.keys()
    )

    for c in challenges:
        task_info = onboarding_task_info_by_challenge[str(c.pk)]

        if task_info.num_is_overdue:
            send_onboarding_task_overdue_alert(
                challenge=c,
                task_info=task_info,
            )

        if task_info.num_is_overdue_soon:
            send_onboarding_task_due_reminder(
                challenge=c,
                task_info=task_info,
            )

        if task_info.num_support_is_overdue:
            send_onboarding_task_support_overdue_alert(
                challenge=c, task_info=task_info
            )


@lambda_task
def send_challenge_request_draft_reminder_emails():
    requests = ChallengeRequest.objects.filter(
        status=ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
        created__lte=now()
        - settings.CHALLENGE_REQUEST_AGE_START_DRAFT_REMINDER_CUTOFF,
        draft_reminder_count__lt=settings.CHALLENGE_REQUEST_MAX_DRAFT_REMINDERS,
    )

    for request in requests:
        send_challenge_requests_draft_reminder(challenge_request=request)

    requests.update(draft_reminder_count=F("draft_reminder_count") + 1)
