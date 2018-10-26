from collections import defaultdict, namedtuple
from typing import Tuple

from grandchallenge.evaluation.models import Result
from grandchallenge.evaluation.templatetags.evaluation_extras import (
    get_jsonpath
)


def generate_rank_dict(
    queryset: Tuple[Result, ...],
    metric_paths: Tuple[str, ...],
    metric_reverse: Tuple[bool, ...],
):
    """
    Generates a dictionary that contains the ranking of results based on a
    given metric path.
    """
    rank = defaultdict(dict)
    pk_val = namedtuple("pk_val", ["pk", "val"])

    for (metric_path, reverse) in zip(metric_paths, metric_reverse):
        # Extract the value of the metric for this primary key and sort on the
        # value of the metric
        pk_vals = [
            pk_val(str(res.pk), get_jsonpath(res.metrics, metric_path))
            for res in queryset
            if get_jsonpath(res.metrics, metric_path) != ""
        ]
        pk_vals.sort(key=lambda x: x.val, reverse=reverse)

        # Assign the ranks
        try:
            current_val = pk_vals[0].val
            current_rank = 1
        except IndexError:
            # No results to work with for this metric
            continue

        for idx, result_pk_val in enumerate(pk_vals):

            # If the values of the metrics are the same, keep the rank
            # position the same
            if result_pk_val.val != current_val:
                current_val = result_pk_val.val
                current_rank = idx + 1

            rank[result_pk_val.pk][metric_path] = current_rank

    return rank
