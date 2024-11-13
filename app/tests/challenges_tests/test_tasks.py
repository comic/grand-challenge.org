import pytest

from grandchallenge.challenges.models import Challenge, ChallengeRequest
from grandchallenge.challenges.tasks import update_challenge_results_cache
from tests.evaluation_tests.factories import EvaluationFactory
from tests.factories import ChallengeFactory, ChallengeRequestFactory


@pytest.mark.django_db
def test_challenge_update(two_challenge_sets, django_assert_num_queries):
    c1 = two_challenge_sets.challenge_set_1.challenge
    c2 = two_challenge_sets.challenge_set_2.challenge

    _ = EvaluationFactory(
        submission__phase__challenge=c1,
        method__phase__challenge=c1,
        time_limit=60,
    )
    _ = EvaluationFactory(
        submission__phase__challenge=c2,
        method__phase__challenge=c2,
        time_limit=60,
    )

    with django_assert_num_queries(4) as _:
        update_challenge_results_cache()

    # check the # queries stays the same even with more challenges & evaluations

    c3 = ChallengeFactory()
    _ = EvaluationFactory(
        submission__phase__challenge=c3,
        method__phase__challenge=c3,
        time_limit=60,
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


def test_challenge_request_budget_calculation(settings):
    settings.COMPONENTS_DEFAULT_BACKEND = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"
    challenge_request = ChallengeRequest(
        expected_number_of_teams=10,
        inference_time_limit_in_minutes=10,
        average_size_of_test_image_in_mb=100,
        phase_1_number_of_submissions_per_team=10,
        phase_2_number_of_submissions_per_team=100,
        phase_1_number_of_test_images=100,
        phase_2_number_of_test_images=500,
        number_of_tasks=1,
    )

    assert challenge_request.budget == {
        "Compute costs for phase 1": 1960,
        "Compute costs for phase 2": 97910,
        "Data storage cost for phase 1": 10,
        "Data storage cost for phase 2": 40,
        "Docker storage cost": 4440,
        "Total across phases": 109360,
        "Total phase 1": 1970,
        "Total phase 2": 97950,
    }

    assert (
        challenge_request.budget["Total phase 2"]
        == challenge_request.budget["Data storage cost for phase 2"]
        + challenge_request.budget["Compute costs for phase 2"]
    )
    assert (
        challenge_request.budget["Total phase 1"]
        == challenge_request.budget["Data storage cost for phase 1"]
        + challenge_request.budget["Compute costs for phase 1"]
    )
    assert (
        challenge_request.budget["Total across phases"]
        == challenge_request.budget["Total phase 1"]
        + challenge_request.budget["Total phase 2"]
        + challenge_request.budget["Docker storage cost"]
    )

    challenge_request.number_of_tasks = 2

    del challenge_request.budget

    assert challenge_request.budget == {
        "Compute costs for phase 1": 3920,
        "Compute costs for phase 2": 195820,
        "Data storage cost for phase 1": 20,
        "Data storage cost for phase 2": 70,
        "Docker storage cost": 8880,
        "Total across phases": 213710,
        "Total phase 1": 3940,
        "Total phase 2": 195890,
    }
    assert (
        challenge_request.budget["Total phase 2"]
        == challenge_request.budget["Data storage cost for phase 2"]
        + challenge_request.budget["Compute costs for phase 2"]
    )
    assert (
        challenge_request.budget["Total phase 1"]
        == challenge_request.budget["Data storage cost for phase 1"]
        + challenge_request.budget["Compute costs for phase 1"]
    )
    assert (
        challenge_request.budget["Total across phases"]
        == challenge_request.budget["Total phase 1"]
        + challenge_request.budget["Total phase 2"]
        + challenge_request.budget["Docker storage cost"]
    )
