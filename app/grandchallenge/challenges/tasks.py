import functools
import random
import time
from typing import NamedTuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Max, Min, Q
from django.utils.timezone import datetime, now
from lambda_tasks.decorators import lambda_task
from lambda_tasks.settings import MAX_DELAY
from psycopg.errors import LockNotAvailable

from grandchallenge.challenges.costs import (
    annotate_challenge_compute_costs,
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
from grandchallenge.core.celery import acks_late_2xlarge_task
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


def retry_with_backoff(exceptions, max_attempts=5, base_delay=1, max_delay=10):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == max_attempts:
                        raise

                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay)
                    total_delay = delay + jitter

                    time.sleep(total_delay)

        return wrapper

    return decorator


@acks_late_2xlarge_task
def update_challenge_compute_costs():
    # TODO: remove the loop and do this live once the challenge.compute_cost_euro_millicents field is removed or deprecated
    for challenge in Challenge.objects.with_available_compute().iterator(
        chunk_size=1000
    ):
        with transaction.atomic():
            annotate_challenge_compute_costs(challenge=challenge)

            @retry_with_backoff((LockNotAvailable,))
            def save_challenge():
                challenge.save(update_fields=("compute_cost_euro_millicents",))

            save_challenge()

    for invoice in Invoice.objects.iterator(chunk_size=1000):
        with transaction.atomic():
            annotate_invoice_compute_costs(invoice=invoice)

            @retry_with_backoff((LockNotAvailable,))
            def save_invoice():
                invoice.save(update_fields=("compute_cost_euro_millicents",))

            save_invoice()

    for phase in Phase.objects.iterator(chunk_size=1000):
        with transaction.atomic():
            annotate_job_duration_and_compute_costs(phase=phase)

            @retry_with_backoff((LockNotAvailable,))
            def save_phase():
                phase.save(
                    skip_calculate_ranks=True,
                    update_fields=(
                        "average_algorithm_job_duration",
                        "compute_cost_euro_millicents",
                    ),
                )

            save_phase()


@lambda_task
def update_challenge_storage_sizes():
    for idx, challenge in enumerate(Challenge.objects.only("pk")):
        update_challenge_storage_size.execute_on_commit(
            pk=challenge.pk,
            _delay=idx % MAX_DELAY,
        )


@lambda_task(singleton=True, retry_on=(LockNotAvailable,))
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
    for c in ChallengeRequest.objects.filter(
        status=ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
        created__lte=now()
        - settings.CHALLENGE_REQUEST_AGE_START_REMINDER_CUTOFF,
        created__gte=now()
        - settings.CHALLENGE_REQUEST_AGE_END_REMINDER_CUTOFF,
    ):
        send_challenge_requests_draft_reminder(challenge_request=c)
