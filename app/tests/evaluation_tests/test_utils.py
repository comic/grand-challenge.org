import pytest
from django.db.models.signals import post_save
from factory.django import mute_signals

from grandchallenge.evaluation.models import Config
from tests.factories import ResultFactory, ChallengeFactory, UserFactory


@pytest.mark.django_db
def test_calculate_ranks(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    challenge = ChallengeFactory()

    with mute_signals(post_save):
        queryset = (
            ResultFactory(challenge=challenge, metrics={"a": 0.1, "b": 0.1}),
            ResultFactory(challenge=challenge, metrics={"a": 0.5, "b": 0.2}),
            ResultFactory(challenge=challenge, metrics={"a": 1.0, "b": 0.3}),
            ResultFactory(challenge=challenge, metrics={"a": 0.7, "b": 0.4}),
            ResultFactory(challenge=challenge, metrics={"a": 0.5, "b": 0.5}),
            # Following two are invalid if relative ranking is used
            ResultFactory(challenge=challenge, metrics={"a": 1.0}),
            ResultFactory(challenge=challenge, metrics={"b": 0.3}),
            # Add a valid, but unpublished result
            ResultFactory(challenge=challenge, metrics={"a": 0.1, "b": 0.1}),
        )

        # Unpublish the result
        queryset[-1].published = False
        queryset[-1].save()

    expected_ranks = {
        Config.DESCENDING: {
            Config.ABSOLUTE: {
                Config.DESCENDING: [6, 4, 1, 3, 4, 1, 0, 0],
                Config.ASCENDING: [6, 4, 1, 3, 4, 1, 0, 0],
            },
            Config.MEDIAN: {
                Config.DESCENDING: [5, 4, 1, 1, 1, 0, 0, 0],
                Config.ASCENDING: [3, 2, 1, 3, 5, 0, 0, 0],
            },
            Config.MEAN: {
                Config.DESCENDING: [5, 4, 1, 1, 1, 0, 0, 0],
                Config.ASCENDING: [3, 2, 1, 3, 5, 0, 0, 0],
            },
        },
        Config.ASCENDING: {
            Config.ABSOLUTE: {
                Config.DESCENDING: [1, 2, 5, 4, 2, 5, 0, 0],
                Config.ASCENDING: [1, 2, 5, 4, 2, 5, 0, 0],
            },
            Config.MEDIAN: {
                Config.DESCENDING: [2, 2, 5, 2, 1, 0, 0, 0],
                Config.ASCENDING: [1, 2, 4, 4, 3, 0, 0, 0],
            },
            Config.MEAN: {
                Config.DESCENDING: [2, 2, 5, 2, 1, 0, 0, 0],
                Config.ASCENDING: [1, 2, 4, 4, 3, 0, 0, 0],
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
                    expected_ranks[a_order][score_method][b_order], queryset
                )


@pytest.mark.django_db
def test_results_display(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    challenge = ChallengeFactory()

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

    challenge.evaluation_config.score_jsonpath = "a"
    challenge.evaluation_config.result_display_choice = Config.ALL
    challenge.evaluation_config.save()

    expected_ranks = [0, 1, 3, 5, 6, 2, 4]
    assert_ranks(expected_ranks, queryset)

    challenge.evaluation_config.result_display_choice = Config.MOST_RECENT
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 2, 0, 0, 1]
    assert_ranks(expected_ranks, queryset)

    challenge.evaluation_config.result_display_choice = Config.BEST
    challenge.evaluation_config.save()

    expected_ranks = [0, 1, 0, 0, 0, 2, 0]
    assert_ranks(expected_ranks, queryset)

    # now test reverse order
    challenge.evaluation_config.score_default_sort = (
        challenge.evaluation_config.ASCENDING
    )
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 2, 1, 0, 0]
    assert_ranks(expected_ranks, queryset)

    challenge.evaluation_config.result_display_choice = Config.MOST_RECENT
    challenge.evaluation_config.save()

    expected_ranks = [0, 0, 0, 1, 0, 0, 2]
    assert_ranks(expected_ranks, queryset)


def assert_ranks(expected_ranks, queryset):
    for r in queryset:
        r.refresh_from_db()

    assert [r.rank for r in queryset] == expected_ranks
