from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Max

from grandchallenge.challenges.models import Challenge, ChallengeRequest
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


def aggregate_compute_costs_per_month_across_challenges(phase_stats):
    monthly_compute_costs = {}
    for _phase, values in phase_stats.items():
        for year, month_values in values.monthly_costs.items():
            for month, cost in month_values.items():
                try:
                    monthly_compute_costs[year][month]["compute_costs"] += cost
                except (KeyError, TypeError):
                    if year not in monthly_compute_costs.keys():
                        monthly_compute_costs[year] = {}
                        monthly_compute_costs[year]["total_compute_cost"] = 0
                        monthly_compute_costs[year]["total_docker_cost"] = 0
                    if month not in monthly_compute_costs[year].keys():
                        monthly_compute_costs[year][month] = {}
                    monthly_compute_costs[year][month]["compute_costs"] = cost
    return monthly_compute_costs


def aggregate_submitted_algorithm_pks_per_month_across_challenges(phase_stats):
    monthly_submitted_algorithms = {}
    for _phase, values in phase_stats.items():
        for (
            year,
            month_values,
        ) in values.algorithm_count_per_month.items():
            for month, algorithm_count in month_values.items():
                try:
                    monthly_submitted_algorithms[year][
                        month
                    ] += algorithm_count
                except (KeyError, TypeError):
                    if year not in monthly_submitted_algorithms.keys():
                        monthly_submitted_algorithms[year] = {}
                    monthly_submitted_algorithms[year][month] = algorithm_count
    return monthly_submitted_algorithms


def add_monthly_docker_costs_to_cost_dict(
    monthly_submitted_algorithms, monthly_compute_costs
):
    ecr_storage_costs = (
        settings.CHALLENGES_ECR_STORAGE_COST_CENTS_PER_TB_PER_YEAR
    )
    average_algorithm_container_size_in_gb = ChallengeRequest._meta.get_field(
        "average_algorithm_container_size_in_gb"
    ).get_default()
    for year, values in monthly_submitted_algorithms.items():
        for month, algorithm_count in values.items():
            cost = round(
                average_algorithm_container_size_in_gb
                * algorithm_count
                * ecr_storage_costs
                / 1000
                / 100,
                ndigits=2,
            )
            monthly_compute_costs[year][month]["docker_costs"] = cost
            monthly_compute_costs[year]["total_docker_cost"] += cost
    return monthly_compute_costs


def get_monthly_challenge_costs(phase_stats):
    monthly_compute_costs = (
        aggregate_compute_costs_per_month_across_challenges(phase_stats)
    )
    monthly_submitted_algorithms = (
        aggregate_submitted_algorithm_pks_per_month_across_challenges(
            phase_stats
        )
    )
    monthly_costs = add_monthly_docker_costs_to_cost_dict(
        monthly_submitted_algorithms, monthly_compute_costs
    )
    for year, values in monthly_costs.items():
        for month, subvals in values.items():
            if month != "total_compute_cost" and month != "total_docker_cost":
                monthly_costs[year][month]["total"] = (
                    subvals["compute_costs"] + subvals["docker_costs"]
                )
                monthly_costs[year]["total_compute_cost"] += subvals[
                    "compute_costs"
                ]
        monthly_costs[year]["grand_total"] = (
            monthly_costs[year]["total_compute_cost"]
            + monthly_costs[year]["total_docker_cost"]
        )
    return monthly_costs


def calculate_costs_per_challenge(phase_stats):
    challenges = Challenge.objects.filter(
        phase__submission_kind=SubmissionKindChoices.ALGORITHM
    ).all()
    ecr_storage_costs = (
        settings.CHALLENGES_ECR_STORAGE_COST_CENTS_PER_TB_PER_YEAR
    )
    average_algorithm_container_size_in_gb = ChallengeRequest._meta.get_field(
        "average_algorithm_container_size_in_gb"
    ).get_default()
    for challenge in challenges:
        submitted_algorithms = [
            str(pk)
            for pk in Submission.objects.filter(
                algorithm_image__isnull=False,
                phase__challenge=challenge,
            ).values_list("algorithm_image__algorithm__pk", flat=True)
        ]
        num_submitted_algorithms = (
            len(list(set(submitted_algorithms))) if submitted_algorithms else 0
        )
        challenge_compute_cost = round(
            sum(
                v.total_phase_compute_cost * 100
                for k, v in phase_stats.items()
                for phase in challenge.phase_set.all()
                if k == str(phase.pk)
                and v.total_phase_compute_cost is not None
            ),
            ndigits=0,
        )
        docker_storage_cost = round(
            average_algorithm_container_size_in_gb
            * num_submitted_algorithms
            * ecr_storage_costs
            / 1000,
            ndigits=0,
        )
        challenge.accumulated_docker_storage_cost_in_cents = (
            docker_storage_cost
        )
        challenge.accumulated_compute_cost_in_cents = challenge_compute_cost
    Challenge.objects.bulk_update(
        challenges,
        [
            "accumulated_docker_storage_cost_in_cents",
            "accumulated_compute_cost_in_cents",
        ],
    )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def update_challenge_cost_statistics():
    phase_stats = cache.get("statistics_for_phases")
    calculate_costs_per_challenge(phase_stats=phase_stats)
    monthly_challenge_costs = get_monthly_challenge_costs(phase_stats)
    cache.set("monthly_challenge_costs", monthly_challenge_costs, timeout=None)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def update_compute_costs_and_storage_size():
    challenges = Challenge.objects.all()

    for c in challenges:
        c.update_size_in_storage_and_registry()
        c.update_compute_cost_euro_millicents()

    Challenge.objects.bulk_update(
        challenges,
        [
            "size_in_storage",
            "size_in_registry",
            "compute_cost_euro_millicents",
        ],
    )


@shared_task(
    **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"],
    name="update_compute_costs_and_storage_size",
)
def null_task():
    # Drop erroneously created tasks
    pass
