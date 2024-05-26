import pytest

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.evaluation.models import Evaluation, Phase
from grandchallenge.evaluation.tasks import calculate_ranks
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "score_method, a_order, b_order, expected_ranks, expected_rank_scores",
    (
        (
            Phase.ABSOLUTE,
            Phase.DESCENDING,
            Phase.DESCENDING,
            [5, 3, 1, 2, 3, 0, 0, 0],
            [5, 3, 1, 2, 3, 0, 0, 0],
        ),
        (
            Phase.ABSOLUTE,
            Phase.DESCENDING,
            Phase.ASCENDING,
            [5, 3, 1, 2, 3, 0, 0, 0],
            [5, 3, 1, 2, 3, 0, 0, 0],
        ),
        (
            Phase.MEDIAN,
            Phase.DESCENDING,
            Phase.DESCENDING,
            [5, 4, 1, 1, 1, 0, 0, 0],
            [5, 3.5, 2, 2, 2, 0, 0, 0],
        ),
        (
            Phase.MEDIAN,
            Phase.DESCENDING,
            Phase.ASCENDING,
            [3, 2, 1, 3, 5, 0, 0, 0],
            [3, 2.5, 2, 3, 4, 0, 0, 0],
        ),
        (
            Phase.MEAN,
            Phase.DESCENDING,
            Phase.DESCENDING,
            [5, 4, 1, 1, 1, 0, 0, 0],
            [5, 3.5, 2, 2, 2, 0, 0, 0],
        ),
        (
            Phase.MEAN,
            Phase.DESCENDING,
            Phase.ASCENDING,
            [3, 2, 1, 3, 5, 0, 0, 0],
            [3, 2.5, 2, 3, 4, 0, 0, 0],
        ),
        (
            Phase.ABSOLUTE,
            Phase.ASCENDING,
            Phase.DESCENDING,
            [1, 2, 5, 4, 2, 0, 0, 0],
            [1, 2, 5, 4, 2, 0, 0, 0],
        ),
        (
            Phase.ABSOLUTE,
            Phase.ASCENDING,
            Phase.ASCENDING,
            [1, 2, 5, 4, 2, 0, 0, 0],
            [1, 2, 5, 4, 2, 0, 0, 0],
        ),
        (
            Phase.MEDIAN,
            Phase.ASCENDING,
            Phase.DESCENDING,
            [2, 2, 5, 2, 1, 0, 0, 0],
            [3, 3, 4, 3, 1.5, 0, 0, 0],
        ),
        (
            Phase.MEDIAN,
            Phase.ASCENDING,
            Phase.ASCENDING,
            [1, 2, 4, 4, 3, 0, 0, 0],
            [1, 2, 4, 4, 3.5, 0, 0, 0],
        ),
        (
            Phase.MEAN,
            Phase.ASCENDING,
            Phase.DESCENDING,
            [2, 2, 5, 2, 1, 0, 0, 0],
            [3, 3, 4, 3, 1.5, 0, 0, 0],
        ),
        (
            Phase.MEAN,
            Phase.ASCENDING,
            Phase.ASCENDING,
            [1, 2, 4, 4, 3, 0, 0, 0],
            [1, 2, 4, 4, 3.5, 0, 0, 0],
        ),
    ),
)
def test_calculate_ranks(
    django_assert_max_num_queries,
    score_method,
    a_order,
    b_order,
    expected_ranks,
    expected_rank_scores,
):
    phase = PhaseFactory()

    results = [
        # Warning: Do not change these values without updating the
        # expected above.
        {"a": 0.0, "b": 0.0},
        {"a": 0.5, "b": 0.2},
        {"a": 1.0, "b": 0.3},
        {"a": 0.7, "b": 0.4},
        {"a": 0.5, "b": 0.5},
        # Following two are invalid as they are incomplete
        {"a": 1.0},
        {"b": 0.3},
        # Add a valid, but unpublished result
        {"a": 0.1, "b": 0.1},
    ]

    queryset = [
        EvaluationFactory(submission__phase=phase, status=Evaluation.SUCCESS)
        for _ in range(len(results))
    ]

    for e, r in zip(queryset, results, strict=True):
        e.outputs.add(
            ComponentInterfaceValue.objects.create(
                interface=ComponentInterface.objects.get(
                    slug="metrics-json-file"
                ),
                value=r,
            )
        )

    # Unpublish the result
    queryset[-1].published = False
    queryset[-1].save()

    # Setup Phase
    phase.score_jsonpath = "a"
    phase.scoring_method_choice = score_method
    phase.score_default_sort = a_order
    phase.extra_results_columns = [
        {"path": "b", "title": "b", "order": b_order}
    ]
    phase.save()

    with django_assert_max_num_queries(10):
        calculate_ranks(phase_pk=phase.pk)

    assert_ranks(
        queryset,
        expected_ranks,
        expected_rank_scores,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "score_method, extra_results_columns, expected_ranks, expected_rank_scores",
    (
        (
            Phase.ABSOLUTE,
            [
                b_default := {
                    "path": "b",
                    "title": "b",
                    "order": Phase.DESCENDING,
                    "exclude_from_ranking": False,
                }
            ],
            only_a_expected_ranks := [5, 3, 1, 2, 3, 0],
            only_a_expected_rank_score := [5, 3, 1, 2, 3, 0],
        ),
        (
            Phase.ABSOLUTE,
            [
                {
                    **b_default,
                    "exclude_from_ranking": True,
                }
            ],
            only_a_expected_ranks,
            only_a_expected_rank_score,
        ),
        (
            Phase.MEDIAN,
            [
                {
                    **b_default,
                    "exclude_from_ranking": False,
                }
            ],
            [5, 4, 1, 1, 1, 0],
            [5, 3.5, 2, 2, 2, 0],
        ),
        (
            Phase.MEDIAN,
            [
                {
                    **b_default,
                    "exclude_from_ranking": True,
                }
            ],
            only_a_expected_ranks,
            only_a_expected_rank_score,
        ),
        (
            Phase.MEAN,
            [
                {
                    **b_default,
                    "exclude_from_ranking": False,
                }
            ],
            [5, 4, 1, 1, 1, 0],
            [5, 3.5, 2, 2, 2, 0],
        ),
        (
            Phase.MEAN,
            [
                {
                    **b_default,
                    "exclude_from_ranking": True,
                }
            ],
            only_a_expected_ranks,
            only_a_expected_rank_score,
        ),
        (
            Phase.MEAN,
            [
                {  # Check if by default it is not excluded from ranking
                    "path": "b",
                    "title": "b",
                    "order": Phase.DESCENDING,
                }
            ],
            [5, 4, 1, 1, 1, 0],
            [5, 3.5, 2, 2, 2, 0],
        ),
    ),
)
def test_calculate_ranks_with_exclusion(
    django_assert_max_num_queries,
    score_method,
    extra_results_columns,
    expected_ranks,
    expected_rank_scores,
):
    phase = PhaseFactory()

    results = [
        # Warning: Do not change this values without updating the
        # expected_ranks/expected_rank_scores above.
        {"a": 0.0, "b": 0.0},
        {"a": 0.5, "b": 0.2},
        {"a": 1.0, "b": 0.3},
        {"a": 0.7, "b": 0.4},
        {"a": 0.5, "b": 0.5},
        {"b": 0.3},  # Incomplete and should not be processed
    ]

    queryset = [
        EvaluationFactory(submission__phase=phase, status=Evaluation.SUCCESS)
        for _ in range(len(results))
    ]

    for e, r in zip(queryset, results, strict=True):
        e.outputs.add(
            ComponentInterfaceValue.objects.create(
                interface=ComponentInterface.objects.get(
                    slug="metrics-json-file"
                ),
                value=r,
            )
        )

    phase.score_jsonpath = "a"
    phase.scoring_method_choice = score_method
    phase.score_default_sort = Phase.DESCENDING
    phase.extra_results_columns = extra_results_columns

    phase.save()

    with django_assert_max_num_queries(10):
        assert calculate_ranks(phase_pk=phase.pk) is None

    assert_ranks(
        queryset,
        expected_ranks,
        expected_rank_scores,
    )


@pytest.mark.django_db
def test_results_display():
    phase = PhaseFactory()

    user1 = UserFactory()
    user2 = UserFactory()

    metrics = "metrics"
    creator = "creator"

    results = [
        {metrics: {"b": 0.3}, creator: user1},  # Invalid result
        {metrics: {"a": 0.6}, creator: user1},
        {metrics: {"a": 0.4}, creator: user1},
        {metrics: {"a": 0.2}, creator: user1},
        {metrics: {"a": 0.1}, creator: user2},
        {metrics: {"a": 0.5}, creator: user2},
        {metrics: {"a": 0.3}, creator: user2},
    ]

    queryset = [
        EvaluationFactory(
            submission__phase=phase,
            submission__creator=r[creator],
            status=Evaluation.SUCCESS,
        )
        for r in results
    ]

    for e, r in zip(queryset, results, strict=True):
        e.outputs.add(
            ComponentInterfaceValue.objects.create(
                interface=ComponentInterface.objects.get(
                    slug="metrics-json-file"
                ),
                value=r[metrics],
            )
        )

    phase.score_jsonpath = "a"
    phase.result_display_choice = Phase.ALL
    phase.save()

    calculate_ranks(phase_pk=phase.pk)

    expected_ranks = [0, 1, 3, 5, 6, 2, 4]
    assert_ranks(queryset, expected_ranks)

    phase.result_display_choice = Phase.MOST_RECENT
    phase.save()

    calculate_ranks(phase_pk=phase.pk)

    expected_ranks = [0, 0, 0, 2, 0, 0, 1]
    assert_ranks(queryset, expected_ranks)

    phase.result_display_choice = Phase.BEST
    phase.save()

    calculate_ranks(phase_pk=phase.pk)

    expected_ranks = [0, 1, 0, 0, 0, 2, 0]
    assert_ranks(queryset, expected_ranks)

    # now test reverse order
    phase.score_default_sort = phase.ASCENDING
    phase.save()

    calculate_ranks(phase_pk=phase.pk)

    expected_ranks = [0, 0, 0, 2, 1, 0, 0]
    assert_ranks(queryset, expected_ranks)

    phase.result_display_choice = Phase.MOST_RECENT
    phase.save()

    calculate_ranks(phase_pk=phase.pk)

    expected_ranks = [0, 0, 0, 1, 0, 0, 2]
    assert_ranks(queryset, expected_ranks)


@pytest.mark.django_db
def test_null_results():
    phase = PhaseFactory()

    results = [{"a": 0.6}, {"a": None}]

    queryset = [
        EvaluationFactory(submission__phase=phase, status=Evaluation.SUCCESS)
        for _ in range(len(results))
    ]

    for e, r in zip(queryset, results, strict=True):
        e.outputs.add(
            ComponentInterfaceValue.objects.create(
                interface=ComponentInterface.objects.get(
                    slug="metrics-json-file"
                ),
                value=r,
            )
        )

    phase.score_jsonpath = "a"
    phase.result_display_choice = Phase.ALL
    phase.save()

    calculate_ranks(phase_pk=phase.pk)

    expected_ranks = [1, 0]
    assert_ranks(queryset, expected_ranks)


def assert_ranks(queryset, expected_ranks, expected_rank_scores=None):
    for r in queryset:
        r.refresh_from_db()

    assert [r.rank for r in queryset] == expected_ranks

    if expected_rank_scores:
        assert [r.rank_score for r in queryset] == expected_rank_scores
