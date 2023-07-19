import datetime
import math

import pytest
from django.conf import settings

from grandchallenge.challenges.models import Challenge
from grandchallenge.challenges.tasks import (
    calculate_costs_per_challenge,
    get_monthly_challenge_costs,
    update_challenge_results_cache,
)
from grandchallenge.evaluation.tasks import PhaseStatistics
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_challenge_update(
    client, two_challenge_sets, django_assert_num_queries
):
    c1 = two_challenge_sets.challenge_set_1.challenge
    c2 = two_challenge_sets.challenge_set_2.challenge

    _ = EvaluationFactory(
        submission__phase__challenge=c1, method__phase__challenge=c1
    )
    _ = EvaluationFactory(
        submission__phase__challenge=c2, method__phase__challenge=c2
    )

    with django_assert_num_queries(4) as _:
        update_challenge_results_cache()

    # check the # queries stays the same even with more challenges & evaluations

    c3 = ChallengeFactory()
    _ = EvaluationFactory(
        submission__phase__challenge=c3, method__phase__challenge=c3
    )
    with django_assert_num_queries(4) as _:
        update_challenge_results_cache()


@pytest.mark.django_db
def test_challenge_creation_from_request(challenge_request):
    # an algorithm submission phase gets created
    challenge_request.create_challenge()
    assert Challenge.objects.count() == 1
    challenge = Challenge.objects.get()
    assert challenge.short_name == challenge_request.short_name
    # requester is admin of challenge
    assert challenge_request.creator in challenge.admins_group.user_set.all()


@pytest.mark.django_db
def test_challenge_request_budget_calculation(challenge_request):
    assert (
        challenge_request.budget["Data storage cost for phase 1"]
        == math.ceil(
            challenge_request.phase_1_number_of_test_images
            * challenge_request.average_size_of_test_image_in_mb
            * settings.CHALLENGES_S3_STORAGE_COST_CENTS_PER_TB_PER_YEAR
            / 1000000
            / 100
            / 10
        )
        * 10
    )
    assert (
        challenge_request.budget["Compute costs for phase 1"]
        == math.ceil(
            challenge_request.phase_1_number_of_submissions_per_team
            * challenge_request.expected_number_of_teams
            * challenge_request.phase_1_number_of_test_images
            * challenge_request.inference_time_limit_in_minutes
            * settings.CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR
            / 60
            / 100
            / 10
        )
        * 10
    )
    assert (
        challenge_request.budget["Compute costs for phase 2"]
        == math.ceil(
            challenge_request.phase_2_number_of_submissions_per_team
            * challenge_request.expected_number_of_teams
            * challenge_request.phase_2_number_of_test_images
            * challenge_request.inference_time_limit_in_minutes
            * settings.CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR
            / 60
            / 100
            / 10
        )
        * 10
    )
    assert (
        challenge_request.budget["Data storage cost for phase 2"]
        == math.ceil(
            challenge_request.phase_2_number_of_test_images
            * challenge_request.average_size_of_test_image_in_mb
            * settings.CHALLENGES_S3_STORAGE_COST_CENTS_PER_TB_PER_YEAR
            / 1000000
            / 100
            / 10
        )
        * 10
    )
    assert (
        challenge_request.budget["Total phase 2"]
        == challenge_request.budget["Data storage cost for phase 2"]
        + challenge_request.budget["Compute costs for phase 2"]
    )
    assert (
        challenge_request.budget["Docker storage cost"]
        == math.ceil(
            challenge_request.average_algorithm_container_size_in_gb
            * challenge_request.average_number_of_containers_per_team
            * challenge_request.expected_number_of_teams
            * settings.CHALLENGES_ECR_STORAGE_COST_CENTS_PER_TB_PER_YEAR
            / 1000
            / 100
            / 10
        )
        * 10
    )
    assert (
        challenge_request.budget["Total phase 1"]
        == challenge_request.budget["Data storage cost for phase 1"]
        + challenge_request.budget["Compute costs for phase 1"]
    )
    assert (
        challenge_request.budget["Total"]
        == challenge_request.budget["Total phase 1"]
        + challenge_request.budget["Total phase 2"]
        + challenge_request.budget["Docker storage cost"]
        + challenge_request.budget["Base cost"]
    )


@pytest.mark.django_db
def test_challenge_costs_calculation():
    ch1, ch2 = ChallengeFactory.create_batch(2)
    phase1 = PhaseFactory(challenge=ch1)
    phase2 = PhaseFactory(challenge=ch2)
    phase1.submission_kind = SubmissionKindChoices.ALGORITHM
    phase2.submission_kind = SubmissionKindChoices.ALGORITHM
    phase1.save()
    phase2.save()
    s1, s2 = SubmissionFactory.create_batch(2, phase=phase1)
    s3, s4, s5 = SubmissionFactory.create_batch(3, phase=phase2)
    for s in [s1, s2, s3, s4, s5]:
        s.algorithm_image = AlgorithmImageFactory()
        s.save()

    phase_stats = {
        str(phase1.pk): PhaseStatistics(
            challenge_title=ch1.title,
            average_algorithm_job_run_time=datetime.timedelta(
                seconds=4191, microseconds=428591
            ),
            accumulated_algorithm_job_run_time=datetime.timedelta(
                days=1, seconds=30960, microseconds=542
            ),
            average_submission_compute_cost=16.3,
            total_phase_compute_cost=32.6,
            archive_item_count=14,
            monthly_costs={
                2021: {
                    "January": 0,
                    "February": 0,
                    "March": 0,
                    "April": 0,
                    "May": 0,
                    "June": 0,
                    "July": 0,
                    "August": 0,
                    "September": 0,
                    "October": 0,
                    "November": 0,
                    "December": 0,
                },
                2022: {
                    "January": 0,
                    "February": 0,
                    "March": 0,
                    "April": 0,
                    "May": 0,
                    "June": 0,
                    "July": 0,
                    "August": 0,
                    "September": 0,
                    "October": 0,
                    "November": 32.6,
                },
            },
            algorithm_count_per_month={
                2021: {
                    "January": 0,
                    "February": 0,
                    "March": 0,
                    "April": 0,
                    "May": 0,
                    "June": 0,
                    "July": 0,
                    "August": 0,
                    "September": 0,
                    "October": 0,
                    "November": 0,
                    "December": 0,
                },
                2022: {
                    "January": 0,
                    "February": 0,
                    "March": 0,
                    "April": 0,
                    "May": 0,
                    "June": 0,
                    "July": 0,
                    "August": 0,
                    "September": 0,
                    "October": 0,
                    "November": 2,
                },
            },
        ),
        str(phase2.pk): PhaseStatistics(
            challenge_title=ch2.title,
            average_algorithm_job_run_time=datetime.timedelta(
                seconds=4407, microseconds=272750
            ),
            accumulated_algorithm_job_run_time=datetime.timedelta(
                days=2, seconds=21120, microseconds=1006
            ),
            average_submission_compute_cost=13.47,
            total_phase_compute_cost=53.87,
            archive_item_count=11,
            monthly_costs={
                2021: {
                    "January": 0,
                    "February": 0,
                    "March": 0,
                    "April": 0,
                    "May": 0,
                    "June": 0,
                    "July": 0,
                    "August": 0,
                    "September": 0,
                    "October": 0,
                    "November": 0,
                    "December": 0,
                },
                2022: {
                    "January": 0,
                    "February": 0,
                    "March": 0,
                    "April": 0,
                    "May": 0,
                    "June": 0,
                    "July": 0,
                    "August": 0,
                    "September": 0,
                    "October": 53.87,
                    "November": 0,
                },
            },
            algorithm_count_per_month={
                2021: {
                    "January": 0,
                    "February": 0,
                    "March": 0,
                    "April": 0,
                    "May": 0,
                    "June": 0,
                    "July": 0,
                    "August": 0,
                    "September": 0,
                    "October": 0,
                    "November": 0,
                    "December": 0,
                },
                2022: {
                    "January": 0,
                    "February": 0,
                    "March": 0,
                    "April": 0,
                    "May": 0,
                    "June": 0,
                    "July": 0,
                    "August": 0,
                    "September": 0,
                    "October": 3,
                    "November": 0,
                },
            },
        ),
    }
    monthly_challenge_costs = get_monthly_challenge_costs(phase_stats)
    assert monthly_challenge_costs[2021]["total_compute_cost"] == 0
    assert monthly_challenge_costs[2022]["total_compute_cost"] == 86.47
    assert monthly_challenge_costs[2022]["total_docker_cost"] == 9.6
    assert monthly_challenge_costs[2022]["grand_total"] == 96.07

    calculate_costs_per_challenge(phase_stats)
    ch1.refresh_from_db()
    ch2.refresh_from_db()
    assert ch1.accumulated_compute_cost_in_cents == 3260
    assert ch1.accumulated_docker_storage_cost_in_cents == 384
    assert ch2.accumulated_compute_cost_in_cents == 5387
    assert ch2.accumulated_docker_storage_cost_in_cents == 576
