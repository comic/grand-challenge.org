import math

import pytest
from django.conf import settings

from grandchallenge.challenges.models import Challenge
from grandchallenge.challenges.tasks import update_challenge_results_cache
from tests.evaluation_tests.factories import EvaluationFactory
from tests.factories import ChallengeFactory, ChallengeRequestFactory


@pytest.mark.django_db
def test_challenge_update(two_challenge_sets, django_assert_num_queries):
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
def test_challenge_creation_from_request():
    challenge_request = ChallengeRequestFactory()
    # an algorithm submission phase gets created
    challenge_request.create_challenge()
    assert Challenge.objects.count() == 1
    challenge = Challenge.objects.get()
    assert challenge.short_name == challenge_request.short_name
    # requester is admin of challenge
    assert challenge_request.creator in challenge.admins_group.user_set.all()


@pytest.mark.django_db
def test_challenge_request_budget_calculation():
    challenge_request = ChallengeRequestFactory()
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
