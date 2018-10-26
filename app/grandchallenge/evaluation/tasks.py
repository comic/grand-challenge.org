import uuid

from celery import shared_task
from django.db.models import Q

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Result, Config
from grandchallenge.evaluation.utils import generate_rank_dict


@shared_task
def calculate_ranks(*, challenge_pk: uuid.UUID):
    challenge = Challenge.objects.get(pk=challenge_pk)

    valid_results = (
        Result.objects.filter(Q(challenge=challenge), Q(published=True))
        .order_by("-created")
        .select_related("job__submission")
    )

    if challenge.evaluation_config.result_display_choice == Config.MOST_RECENT:
        # Go through the results and only pass through the most recent
        # submission for each user
        users_seen = set()
        queryset = []

        for r in valid_results:
            creator = r.job.submission.creator

            if creator not in users_seen:
                users_seen.add(creator)
                queryset.append(r)

    else:
        queryset = valid_results

    ranks = generate_rank_dict(
        queryset=queryset,
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
            # This result will be excluded from the display
            rank = 0

        Result.objects.filter(pk=res.pk).update(rank=rank)

    return ranks
