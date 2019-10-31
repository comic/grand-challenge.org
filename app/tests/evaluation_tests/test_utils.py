import pytest
from django.db.models.signals import post_save
from factory.django import mute_signals

from grandchallenge.evaluation.models import Config
from tests.factories import ChallengeFactory, ResultFactory, UserFactory


@pytest.mark.django_db
def test_calculate_ranks(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    challenge = ChallengeFactory()

    with mute_signals(post_save):
        queryset = (
            # Warning: Do not change this values without updating the
            # expected_ranks below.
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.0, "b": 0.0},
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.5, "b": 0.2},
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 1.0, "b": 0.3},
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.7, "b": 0.4},
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.5, "b": 0.5},
            ),
            # Following two are invalid if relative ranking is used
            ResultFactory(
                job__submission__challenge=challenge, metrics={"a": 1.0}
            ),
            ResultFactory(
                job__submission__challenge=challenge, metrics={"b": 0.3}
            ),
            # Add a valid, but unpublished result
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.1, "b": 0.1},
            ),
        )

        # Unpublish the result
        queryset[-1].published = False
        queryset[-1].save()

    expected = {
        Config.DESCENDING: {
            Config.ABSOLUTE: {
                Config.DESCENDING: {
                    "ranks": [6, 4, 1, 3, 4, 1, 0, 0],
                    "rank_scores": [6, 4, 1, 3, 4, 1, 0, 0],
                },
                Config.ASCENDING: {
                    "ranks": [6, 4, 1, 3, 4, 1, 0, 0],
                    "rank_scores": [6, 4, 1, 3, 4, 1, 0, 0],
                },
            },
            Config.MEDIAN: {
                Config.DESCENDING: {
                    "ranks": [5, 4, 1, 1, 1, 0, 0, 0],
                    "rank_scores": [5, 3.5, 2, 2, 2, 0, 0, 0],
                },
                Config.ASCENDING: {
                    "ranks": [3, 2, 1, 3, 5, 0, 0, 0],
                    "rank_scores": [3, 2.5, 2, 3, 4, 0, 0, 0],
                },
            },
            Config.MEAN: {
                Config.DESCENDING: {
                    "ranks": [5, 4, 1, 1, 1, 0, 0, 0],
                    "rank_scores": [5, 3.5, 2, 2, 2, 0, 0, 0],
                },
                Config.ASCENDING: {
                    "ranks": [3, 2, 1, 3, 5, 0, 0, 0],
                    "rank_scores": [3, 2.5, 2, 3, 4, 0, 0, 0],
                },
            },
        },
        Config.ASCENDING: {
            Config.ABSOLUTE: {
                Config.DESCENDING: {
                    "ranks": [1, 2, 5, 4, 2, 5, 0, 0],
                    "rank_scores": [1, 2, 5, 4, 2, 5, 0, 0],
                },
                Config.ASCENDING: {
                    "ranks": [1, 2, 5, 4, 2, 5, 0, 0],
                    "rank_scores": [1, 2, 5, 4, 2, 5, 0, 0],
                },
            },
            Config.MEDIAN: {
                Config.DESCENDING: {
                    "ranks": [2, 2, 5, 2, 1, 0, 0, 0],
                    "rank_scores": [3, 3, 4, 3, 1.5, 0, 0, 0],
                },
                Config.ASCENDING: {
                    "ranks": [1, 2, 4, 4, 3, 0, 0, 0],
                    "rank_scores": [1, 2, 4, 4, 3.5, 0, 0, 0],
                },
            },
            Config.MEAN: {
                Config.DESCENDING: {
                    "ranks": [2, 2, 5, 2, 1, 0, 0, 0],
                    "rank_scores": [3, 3, 4, 3, 1.5, 0, 0, 0],
                },
                Config.ASCENDING: {
                    "ranks": [1, 2, 4, 4, 3, 0, 0, 0],
                    "rank_scores": [1, 2, 4, 4, 3.5, 0, 0, 0],
                },
            },
        },
    }

    for score_method in (Config.ABSOLUTE, Config.MEDIAN, Config.MEAN):
        for a_order in (Config.DESCENDING, Config.ASCENDING):
            for b_order in (Config.DESCENDING, Config.ASCENDING):
                challenge.evaluation_config.score_jsonpath = "a"
                challenge.evaluation_config.scoring_method_choice = (
                    score_method
                )
                challenge.evaluation_config.score_default_sort = a_order
                challenge.evaluation_config.extra_results_columns = [
                    {"path": "b", "title": "b", "order": b_order}
                ]
                challenge.evaluation_config.save()

                assert_ranks(
                    queryset,
                    expected[a_order][score_method][b_order]["ranks"],
                    expected[a_order][score_method][b_order]["rank_scores"],
                )


@pytest.mark.django_db
def test_results_display(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    challenge = ChallengeFactory()

    with mute_signals(post_save):
        user1 = UserFactory()
        user2 = UserFactory()
        queryset = (
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"b": 0.3},  # Invalid result
                job__submission__creator=user1,
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.6},
                job__submission__creator=user1,
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.4},
                job__submission__creator=user1,
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.2},
                job__submission__creator=user1,
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.1},
                job__submission__creator=user2,
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.5},
                job__submission__creator=user2,
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.3},
                job__submission__creator=user2,
            ),
        )

    challenge.evaluation_config.score_jsonpath = "a"
    challenge.evaluation_config.result_display_choice = Config.ALL
    challenge.evaluation_config.save()

    expected_ranks = [0, 1, 3, 5, 6, 2, 4]
    assert_ranks(queryset, expected_ranks)

    challenge.evaluation_config.result_display_choice = Config.MOST_RECENT
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 2, 0, 0, 1]
    assert_ranks(queryset, expected_ranks)

    challenge.evaluation_config.result_display_choice = Config.BEST
    challenge.evaluation_config.save()

    expected_ranks = [0, 1, 0, 0, 0, 2, 0]
    assert_ranks(queryset, expected_ranks)

    # now test reverse order
    challenge.evaluation_config.score_default_sort = (
        challenge.evaluation_config.ASCENDING
    )
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 2, 1, 0, 0]
    assert_ranks(queryset, expected_ranks)

    challenge.evaluation_config.result_display_choice = Config.MOST_RECENT
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 1, 0, 0, 2]
    assert_ranks(queryset, expected_ranks)


@pytest.mark.django_db
def test_null_results(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    challenge = ChallengeFactory()

    with mute_signals(post_save):
        user1 = UserFactory()
        queryset = (
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": 0.6},
                job__submission__creator=user1,
            ),
            ResultFactory(
                job__submission__challenge=challenge,
                metrics={"a": None},
                job__submission__creator=user1,
            ),
        )

    challenge.evaluation_config.score_jsonpath = "a"
    challenge.evaluation_config.result_display_choice = Config.ALL
    challenge.evaluation_config.save()

    expected_ranks = [1, 0]
    assert_ranks(queryset, expected_ranks)


def assert_ranks(queryset, expected_ranks, expected_rank_scores=None):
    for r in queryset:
        r.refresh_from_db()

    assert [r.rank for r in queryset] == expected_ranks

    if expected_rank_scores:
        assert [r.rank_score for r in queryset] == expected_rank_scores
