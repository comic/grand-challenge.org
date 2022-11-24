from typing import NamedTuple

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Max

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Evaluation, Submission
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


class ChallengeCosts(NamedTuple):
    short_name: str
    status: str
    challenge_compute_cost: float
    docker_storage_cost: float


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def update_challenge_cost_statistics():
    phase_stats = cache.get("statistics_for_phases")
    challenge_dict = {}
    challenges = Challenge.objects.filter(
        phase__submission_kind=SubmissionKindChoices.ALGORITHM
    ).all()
    ecr_storage_costs = (
        settings.CHALLENGES_ECR_STORAGE_COST_CENTS_PER_TB_PER_YEAR
    )
    average_algorithm_container_size_in_gb = 10

    for challenge in challenges:
        submitted_algorithms = Submission.objects.filter(
            algorithm_image__isnull=False,
            phase__challenge=challenge,
        ).values_list("algorithm_image__algorithm__pk", flat=True)
        num_submitted_algorithms = (
            len(list(set(submitted_algorithms))) if submitted_algorithms else 0
        )
        challenge_compute_cost = sum(
            v.total_phase_compute_cost
            for k, v in phase_stats.items()
            for phase in challenge.phase_set.all()
            if k == phase.pk and v.total_phase_compute_cost is not None
        )
        docker_storage_cost = round(
            average_algorithm_container_size_in_gb
            * num_submitted_algorithms
            * ecr_storage_costs
            / 1000
            / 100,
            ndigits=2,
        )
        challenge_dict[challenge.pk] = ChallengeCosts(
            short_name=challenge.short_name,
            status=challenge.status.name,
            challenge_compute_cost=challenge_compute_cost,
            docker_storage_cost=docker_storage_cost,
        )
    cache.set("statistics_for_challenges", challenge_dict, timeout=None)
