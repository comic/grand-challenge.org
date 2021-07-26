import pytest

from grandchallenge.challenges.tasks import update_challenge_results_cache
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
