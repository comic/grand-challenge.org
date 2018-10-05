import uuid

from celery import shared_task
from django.db.models import Q

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Result
from grandchallenge.evaluation.utils import generate_rank_dict


@shared_task
def calculate_ranks(*, challenge_pk: uuid.UUID):
    challenge = Challenge.objects.get(pk=challenge_pk)
    valid_results = Result.objects.filter(
        Q(challenge=challenge), Q(published=True)
    )
    ranks = generate_rank_dict(
        queryset=valid_results,
        metric_paths=(challenge.evaluation_config.score_jsonpath,),
        metric_reverse=(
            challenge.evaluation_config.score_default_sort
            == challenge.evaluation_config.DESCENDING,
        ),
    )
    for res in Result.objects.filter(Q(challenge=challenge)):
        try:
            rank = ranks[str(res.pk)][
                challenge.evaluation_config.score_jsonpath
            ]
        except KeyError:
            rank = 0
        Result.objects.filter(pk=res.pk).update(rank=rank)
    return ranks
