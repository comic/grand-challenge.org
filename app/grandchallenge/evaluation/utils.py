from collections import defaultdict, namedtuple
from typing import Tuple

from grandchallenge.evaluation.models import Result
from grandchallenge.evaluation.templatetags.evaluation_extras import (
    get_jsonpath
)


def generate_ranks(
    *,
    queryset: Tuple[Result, ...],
    metric_paths: Tuple[str, ...],
    metric_reverse: Tuple[bool, ...],
):
    """
    Generates a dictionary that contains the ranking of results based on a
    given metric path.
    """

    metric_rank = defaultdict(dict)

    for (metric_path, reverse) in zip(metric_paths, metric_reverse):
        # Extract the value of the metric for this primary key and sort on the
        # value of the metric
        metric_results = [
            {
                "pk": str(res.pk),
                "value": get_jsonpath(res.metrics, metric_path),
            }
            for res in queryset
            if get_jsonpath(res.metrics, metric_path) != ""
        ]
        metric_results.sort(key=lambda x: x["value"], reverse=reverse)

        # Assign the ranks
        try:
            current_val = metric_results[0]["value"]
            current_rank = 1
        except IndexError:
            # No results to work with for this metric
            continue

        for idx, result in enumerate(metric_results):

            # If the values of the metrics are the same, keep the rank
            # position the same
            if result["value"] != current_val:
                current_val = result["value"]
                current_rank = idx + 1

            metric_rank[result["pk"]][metric_path] = current_rank

    if len(metric_paths) == 1:
        return {pk: r[metric_paths[0]] for pk, r in metric_rank.items()}
    else:
        raise NotImplementedError
