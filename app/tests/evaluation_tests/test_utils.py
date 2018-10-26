import pytest
from django.db.models.signals import post_save
from factory.django import mute_signals

from grandchallenge.evaluation.models import Result, Config
from grandchallenge.evaluation.tasks import calculate_ranks
from tests.factories import ResultFactory, ChallengeFactory, UserFactory


@pytest.mark.django_db
def test_calculate_ranks():
    challenge = ChallengeFactory()
    challenge.evaluation_config.score_jsonpath = "a"
    challenge.evaluation_config.save()

    with mute_signals(post_save):
        queryset = (
            ResultFactory(challenge=challenge, metrics={"a": 0.1}),
            ResultFactory(challenge=challenge, metrics={"a": 0.5}),
            ResultFactory(challenge=challenge, metrics={"a": 1.0}),
            ResultFactory(challenge=challenge, metrics={"a": 0.7}),
            ResultFactory(challenge=challenge, metrics={"a": 0.5}),
            ResultFactory(challenge=challenge, metrics={"a": 1.0}),
            ResultFactory(
                challenge=challenge, metrics={"b": 0.3}  # Invalid result
            ),
        )

    # An alternative implementation could be [4, 3, 1, 2, 3, 1] as there are
    # only 4 unique values, the current implementation is harsh on poor results
    expected_ranks = [6, 4, 1, 3, 4, 1, 0]
    assert_ranks(challenge, expected_ranks, queryset)

    # now test reverse order
    challenge.evaluation_config.score_default_sort = (
        challenge.evaluation_config.ASCENDING
    )
    challenge.evaluation_config.save()

    expected_ranks = [1, 2, 5, 4, 2, 5, 0]
    assert_ranks(challenge, expected_ranks, queryset)


@pytest.mark.django_db
def test_results_display():
    challenge = ChallengeFactory()
    challenge.evaluation_config.score_jsonpath = "a"
    challenge.evaluation_config.result_display_choice = Config.ALL
    challenge.evaluation_config.save()

    with mute_signals(post_save):
        user1 = UserFactory()
        user2 = UserFactory()
        queryset = (
            ResultFactory(
                challenge=challenge,
                metrics={"b": 0.3},  # Invalid result
                job__submission__creator=user1,
            ),
            ResultFactory(
                challenge=challenge,
                metrics={"a": 0.6},
                job__submission__creator=user1,
            ),
            ResultFactory(
                challenge=challenge,
                metrics={"a": 0.4},
                job__submission__creator=user1,
            ),
            ResultFactory(
                challenge=challenge,
                metrics={"a": 0.2},
                job__submission__creator=user1,
            ),
            ResultFactory(
                challenge=challenge,
                metrics={"a": 0.1},
                job__submission__creator=user2,
            ),
            ResultFactory(
                challenge=challenge,
                metrics={"a": 0.5},
                job__submission__creator=user2,
            ),
            ResultFactory(
                challenge=challenge,
                metrics={"a": 0.3},
                job__submission__creator=user2,
            ),
        )

    expected_ranks = [0, 1, 3, 5, 6, 2, 4]
    assert_ranks(challenge, expected_ranks, queryset)

    challenge.evaluation_config.result_display_choice = Config.MOST_RECENT
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 2, 0, 0, 1]
    assert_ranks(challenge, expected_ranks, queryset)

    challenge.evaluation_config.result_display_choice = Config.BEST
    challenge.evaluation_config.save()

    expected_ranks = [0, 1, 0, 0, 0, 2, 0]
    assert_ranks(challenge, expected_ranks, queryset)

    # now test reverse order
    challenge.evaluation_config.score_default_sort = (
        challenge.evaluation_config.ASCENDING
    )
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 2, 1, 0, 0]
    assert_ranks(challenge, expected_ranks, queryset)

    challenge.evaluation_config.result_display_choice = Config.MOST_RECENT
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 1, 0, 0, 2]
    assert_ranks(challenge, expected_ranks, queryset)


def assert_ranks(challenge, expected_ranks, queryset):
    # Execute calculate_ranks manually
    calculate_ranks(challenge_pk=challenge.pk)

    for q, exp in zip(queryset, expected_ranks):
        r = Result.objects.get(pk=q.pk)
        assert r.rank == exp
