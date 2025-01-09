import functools
import random
import time

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Max
from psycopg.errors import LockNotAvailable

from grandchallenge.challenges.costs import (
    annotate_compute_costs_and_storage_size,
    annotate_job_duration_and_compute_costs,
)
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.celery import acks_late_2xlarge_task
from grandchallenge.evaluation.models import Evaluation, Phase


@acks_late_2xlarge_task
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
def update_compute_costs_and_storage_size():
    for challenge in Challenge.objects.with_available_compute().iterator():
        with transaction.atomic():
            annotate_compute_costs_and_storage_size(challenge=challenge)

            @retry_with_backoff((LockNotAvailable,))
            def save_challenge():
                challenge.save(
                    update_fields=(
                        "size_in_storage",
                        "size_in_registry",
                        "compute_cost_euro_millicents",
                    )
                )

            save_challenge()

    for phase in Phase.objects.iterator():
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
