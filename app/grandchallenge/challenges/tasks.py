from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Max

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.tasks import (
    PhaseStatistics,
    get_average_job_duration_for_phase,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices


@shared_task
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


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def update_challenge_cost_statistics():
    Phase = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Phase"
    )
    phases = (
        Phase.objects.filter(submission_kind=SubmissionKindChoices.ALGORITHM)
        .annotate(archive_item_count=Count("archive__items"))
        .all()
    )
    challenge_dict = {}
    for phase in phases:
        avg_duration = get_average_job_duration_for_phase(phase)
        average_algorithm_job_run_time = avg_duration.get(
            "average_duration", None
        )
        accumulated_algorithm_job_run_time = avg_duration.get(
            "total_duration", None
        )
        try:
            average_submission_compute_cost = round(
                phase.archive_item_count
                * average_algorithm_job_run_time.total_seconds()
                * settings.CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR
                / 3600
                / 100,
                ndigits=2,
            )
            total_phase_compute_cost = round(
                accumulated_algorithm_job_run_time.total_seconds()
                * settings.CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR
                / 3600
                / 100,
                ndigits=2,
            )
        except AttributeError:
            average_submission_compute_cost = None
            total_phase_compute_cost = None

        challenge_dict[phase.challenge.title] = {
            phase.pk: PhaseStatistics(
                average_algorithm_job_run_time,
                accumulated_algorithm_job_run_time,
                average_submission_compute_cost,
                total_phase_compute_cost,
                phase.archive_item_count,
            )
        }

    cache.set("statistics_for_challenges", challenge_dict, timeout=None)
