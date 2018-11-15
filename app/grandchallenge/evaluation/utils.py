from typing import Tuple, NamedTuple, List, Callable, Iterable, Dict

from grandchallenge.evaluation.models import Result
from grandchallenge.evaluation.templatetags.evaluation_extras import (
    get_jsonpath
)


class Metric(NamedTuple):
    path: str
    reverse: bool


class Score(NamedTuple):
    pk: str
    value: float


class Positions(NamedTuple):
    ranks: Dict
    rank_scores: Dict
    rank_per_metric: Dict


def _filter_valid_results(
    *, results: Iterable[Result], metrics: Tuple[Metric, ...]
) -> List:
    """ Ensure that all of the metrics are in every result """
    return [
        res
        for res in results
        if all(get_jsonpath(res.metrics, m.path) for m in metrics)
    ]


def _scores_to_ranks(*, scores: List[Score], reverse: bool = False) -> dict:
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


def rank_results(
    *,
    results: Tuple[Result, ...],
    metrics: Tuple[Metric, ...],
    score_method: Callable,
) -> Positions:
    """
    Calculates the overall rank for each result, along with the rank_score
    and the rank per metric.
    """

    results = _filter_valid_results(results=results, metrics=metrics)

    metric_rank = {}
    for metric in metrics:
        # Extract the value of the metric for this primary key and sort on the
        # value of the metric
        metric_scores = [
            Score(pk=str(res.pk), value=get_jsonpath(res.metrics, metric.path))
            for res in results
        ]
        metric_rank[metric.path] = _scores_to_ranks(
            scores=metric_scores, reverse=metric.reverse
        )

    rank_per_metric = {
        str(res.pk): {
            metric_path: ranks[str(res.pk)]
            for metric_path, ranks in metric_rank.items()
        }
        for res in results
    }

    scores = [
        Score(pk=pk, value=score_method([m for m in metrics.values()]))
        for pk, metrics in rank_per_metric.items()
    ]

    return Positions(
        ranks=_scores_to_ranks(scores=scores, reverse=False),
        rank_scores={s.pk: s.value for s in scores},
        rank_per_metric=rank_per_metric,
    )
