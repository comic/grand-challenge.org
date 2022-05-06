import pytest

from config import settings
from grandchallenge.challenges.models import Challenge
from grandchallenge.challenges.tasks import update_challenge_results_cache
from grandchallenge.evaluation.utils import SubmissionKind
from tests.evaluation_tests.factories import EvaluationFactory
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
def test_challenge_creation_from_request(
    type_1_challenge_request, type_2_challenge_request
):
    # for a type 2 challenge, an algorithm submission phase gets created
    type_2_challenge_request.create_challenge()
    assert Challenge.objects.count() == 1
    challenge = Challenge.objects.get()
    assert challenge.short_name == type_2_challenge_request.short_name
    # requester is admin of challenge
    assert (
        type_2_challenge_request.creator
        in challenge.admins_group.user_set.all()
    )
    # an algorithm submission phase has been created
    assert challenge.phase_set.count() == 1
    assert (
        challenge.phase_set.get().submission_kind == SubmissionKind.ALGORITHM
    )

    # for a type 1 challenge, a csv submission phase gets created
    type_1_challenge_request.create_challenge()
    assert Challenge.objects.count() == 2
    challenge2 = Challenge.objects.last()
    assert challenge2.short_name == type_1_challenge_request.short_name
    assert (
        type_1_challenge_request.creator
        in challenge2.admins_group.user_set.all()
    )
    assert challenge2.phase_set.count() == 1
    assert challenge2.phase_set.get().submission_kind == SubmissionKind.CSV


@pytest.mark.django_db
def test_challenge_request_budget_calculation(type_2_challenge_request):
    assert type_2_challenge_request.budget[
        "Data storage cost for phase 1"
    ] == round(
        type_2_challenge_request.phase_1_number_of_test_images
        * type_2_challenge_request.average_size_of_test_image_in_mb
        * settings.CHALLENGES_STORAGE_COST_CENTS_PER_TB_PER_YEAR
        / 1000000
        / 100,
        ndigits=2,
    )
    assert type_2_challenge_request.budget[
        "Compute costs for phase 1"
    ] == round(
        type_2_challenge_request.phase_1_number_of_submissions_per_team
        * type_2_challenge_request.expected_number_of_teams
        * type_2_challenge_request.phase_1_number_of_test_images
        * type_2_challenge_request.inference_time_limit_in_minutes
        * settings.CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR
        / 60
        / 100,
        ndigits=2,
    )
    assert type_2_challenge_request.budget[
        "Compute costs for phase 2"
    ] == round(
        type_2_challenge_request.phase_2_number_of_submissions_per_team
        * type_2_challenge_request.expected_number_of_teams
        * type_2_challenge_request.phase_2_number_of_test_images
        * type_2_challenge_request.inference_time_limit_in_minutes
        * settings.CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR
        / 60
        / 100,
        ndigits=2,
    )
    assert type_2_challenge_request.budget[
        "Data storage cost for phase 2"
    ] == round(
        type_2_challenge_request.phase_2_number_of_test_images
        * type_2_challenge_request.average_size_of_test_image_in_mb
        * settings.CHALLENGES_STORAGE_COST_CENTS_PER_TB_PER_YEAR
        / 1000000
        / 100,
        ndigits=2,
    )
    assert type_2_challenge_request.budget["Total phase 2"] == round(
        type_2_challenge_request.budget["Data storage cost for phase 2"]
        + type_2_challenge_request.budget["Compute costs for phase 2"],
        ndigits=2,
    )
    assert type_2_challenge_request.budget["Docker storage cost"] == round(
        type_2_challenge_request.average_algorithm_container_size_in_gb
        * type_2_challenge_request.average_number_of_containers_per_team
        * type_2_challenge_request.expected_number_of_teams
        * settings.CHALLENGES_STORAGE_COST_CENTS_PER_TB_PER_YEAR
        / 1000
        / 100,
        ndigits=2,
    )
    assert type_2_challenge_request.budget["Total phase 1"] == round(
        type_2_challenge_request.budget["Data storage cost for phase 1"]
        + type_2_challenge_request.budget["Compute costs for phase 1"],
        ndigits=2,
    )
    assert type_2_challenge_request.budget["Total"] == round(
        type_2_challenge_request.budget["Total phase 1"]
        + type_2_challenge_request.budget["Total phase 2"]
        + type_2_challenge_request.budget["Docker storage cost"],
        ndigits=2,
    )
