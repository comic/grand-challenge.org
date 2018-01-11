from typing import Tuple

from evaluation.models import Result
from evaluation.templatetags.evaluation_extras import get_jsonpath


def generate_rank_dict(queryset: Tuple[Result, ...], metrics: Tuple[str, ...]):
    """
    Adds rank annotations to a Result set for the given metrics
    """

    rank = {}

    for q in queryset:
        rank[str(q.pk)] = {}

    for metric in metrics:
        m = [(str(x.pk), get_jsonpath(x.metrics, metric)) for x in queryset]
        m.sort(key=lambda x: x[1], reverse=True)

        for i, q in enumerate(m):
            rank[q[0]][metric] = i + 1

    return rank
