from typing import Tuple, NamedTuple, List, Callable

from grandchallenge.evaluation.models import Result
from grandchallenge.evaluation.templatetags.evaluation_extras import (
    get_jsonpath
)


class Score(NamedTuple):
    pk: str
    value: float


def _filter_valid_results(
    *, queryset: Tuple[Result], metric_paths: Tuple[str, ...]
) -> Tuple:
    """ Ensure that all of the metrics are in every result """
    return tuple(
        res
        for res in queryset
        if all(get_jsonpath(res.metrics, p) for p in metric_paths)
    )


def _scores_to_rank(*, scores: List[Score], reverse: bool = False) -> dict:
    """
    Go from a score (a scalar) to a rank (integer). If two scalars are the
    same then they will have the same rank.
    """
    scores.sort(key=lambda x: x.value, reverse=reverse)

    ranks = {}

    try:
        current_value = scores[0].value
        current_rank = 1
    except IndexError:
        # No valid scores
        return ranks

    for idx, score in enumerate(scores):
        if score.value != current_value:
            current_value = score.value
            current_rank = idx + 1

        ranks[score.pk] = current_rank

    return ranks


def generate_ranks(
    *,
    queryset: Tuple[Result, ...],
    metric_paths: Tuple[str, ...],
    metric_reverse: Tuple[bool, ...],
    score_method: Callable,
) -> dict:
    """
    Generates a dictionary that contains the ranking of results based on a
    given metric path.
    """
    queryset = _filter_valid_results(
        queryset=queryset, metric_paths=metric_paths
    )

    metric_rank = {}
    for (metric_path, reverse) in zip(metric_paths, metric_reverse):
        # Extract the value of the metric for this primary key and sort on the
        # value of the metric
        metric_results = [
            Score(pk=str(res.pk), value=get_jsonpath(res.metrics, metric_path))
            for res in queryset
        ]
        metric_rank[metric_path] = _scores_to_rank(
            scores=metric_results, reverse=reverse
        )

    scores = [
        Score(
            pk=str(res.pk),
            value=score_method(
                [ranks[str(res.pk)] for ranks in metric_rank.values()]
            ),
        )
        for res in queryset
    ]

    return _scores_to_rank(scores=scores, reverse=False)
