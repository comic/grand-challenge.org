from collections import OrderedDict
from typing import Callable, Dict, Iterable, List, NamedTuple, Tuple

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from grandchallenge.evaluation.templatetags.evaluation_extras import (
    get_jsonpath,
)


class Metric(NamedTuple):
    path: str
    reverse: bool


class Positions(NamedTuple):
    ranks: Dict[str, float]
    rank_scores: Dict[str, float]
    rank_per_metric: Dict[str, Dict[str, float]]


def get(inputs):
    """Substitute for queryset.get when the qs already exists."""
    if len(inputs) == 1:
        return inputs[0]
    elif len(inputs) == 0:
        raise ObjectDoesNotExist
    else:
        raise MultipleObjectsReturned


def rank_results(
    *, evaluations: Tuple, metrics: Tuple[Metric, ...], score_method: Callable,
) -> Positions:
    """Determine the overall rank for each result."""
    evaluations = _filter_valid_results(
        evaluations=evaluations, metrics=metrics
    )

    rank_per_metric = _get_rank_per_metric(
        evaluations=evaluations, metrics=metrics
    )

    rank_scores = {
        pk: score_method([m for m in metrics.values()])
        for pk, metrics in rank_per_metric.items()
    }

    return Positions(
        ranks=_scores_to_ranks(scores=rank_scores, reverse=False),
        rank_scores=rank_scores,
        rank_per_metric=rank_per_metric,
    )


def _filter_valid_results(
    *, evaluations: Iterable, metrics: Tuple[Metric, ...]
) -> List:
    """Ensure that all of the metrics are in every result."""
    return [
        e
        for e in evaluations
        if all(
            get_jsonpath(
                get(
                    [
                        o.value
                        for o in e.outputs.all()
                        if o.interface.slug == "metrics-json-file"
                    ]
                ),
                m.path,
            )
            not in ["", None]
            for m in metrics
        )
    ]


def _get_rank_per_metric(
    *, evaluations: Iterable, metrics: Tuple[Metric, ...]
) -> Dict[str, Dict[str, float]]:
    """
    Takes results and calculates the rank for each of the individual metrics

    Returns a dictionary where the key is the pk of the result, and the
    values is another dictionary where the key is the path of the metric and
    the value is the rank of this result for this metric
    """
    metric_rank = {}
    for metric in metrics:
        # Extract the value of the metric for this primary key and sort on the
        # value of the metric
        metric_scores = {
            e.pk: get_jsonpath(
                get(
                    [
                        o.value
                        for o in e.outputs.all()
                        if o.interface.slug == "metrics-json-file"
                    ]
                ),
                metric.path,
            )
            for e in evaluations
        }
        metric_rank[metric.path] = _scores_to_ranks(
            scores=metric_scores, reverse=metric.reverse
        )

    return {
        e.pk: {
            metric_path: ranks[e.pk]
            for metric_path, ranks in metric_rank.items()
        }
        for e in evaluations
    }


def _scores_to_ranks(
    *, scores: Dict, reverse: bool = False
) -> Dict[str, float]:
    """
    Go from a score (a scalar) to a rank (integer). If two scalars are the
    same then they will have the same rank.

    Takes a dictionary where the keys are the pk of the results and the values
    are the scores.

    Outputs a dictionary where they keys are the pk of the results and the
    values are the ranks.
    """
    scores = OrderedDict(
        sorted(scores.items(), key=lambda t: t[1], reverse=reverse)
    )

    ranks = {}
    current_score = current_rank = None

    for idx, (pk, score) in enumerate(scores.items()):
        if score != current_score:
            current_score = score
            current_rank = idx + 1

        ranks[pk] = current_rank

    return ranks
