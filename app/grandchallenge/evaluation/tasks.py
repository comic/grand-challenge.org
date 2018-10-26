import uuid

from celery import shared_task
from django.db.models import Q

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Result, Config
from grandchallenge.evaluation.utils import generate_rank_dict


@shared_task
def calculate_ranks(*, challenge_pk: uuid.UUID):
    challenge = Challenge.objects.get(pk=challenge_pk)
    score_path = challenge.evaluation_config.score_jsonpath
    default_sort = challenge.evaluation_config.score_default_sort
    display_choice = challenge.evaluation_config.result_display_choice

    valid_results = (
        Result.objects.filter(Q(challenge=challenge), Q(published=True))
        .order_by("-created")
        .select_related("job__submission")
    )

    if display_choice == Config.MOST_RECENT:
        # Go through the results and only pass through the most recent
        # submission for each user
        users_seen = set()
        queryset = []

        for r in valid_results:
            creator = r.job.submission.creator

            if creator not in users_seen:
                users_seen.add(creator)
                queryset.append(r)

    elif display_choice == Config.BEST:

        all_ranks = generate_rank_dict(
            queryset=valid_results,
            metric_paths=(score_path,),
            metric_reverse=(default_sort == Config.DESCENDING,),
        )

        best_result_per_user = {}

        for r in valid_results:
            creator = r.job.submission.creator

            try:
                this_rank = all_ranks[str(r.pk)][score_path]
            except KeyError:
                # This result was not ranked
                continue

            if creator not in best_result_per_user or (
                this_rank
                < all_ranks[str(best_result_per_user[creator].pk)][score_path]
            ):
                best_result_per_user[creator] = r

        queryset = [r for r in best_result_per_user.values()]

    else:
        queryset = valid_results

    ranks = generate_rank_dict(
        queryset=queryset,
        metric_paths=(score_path,),
        metric_reverse=(default_sort == Config.DESCENDING,),
    )

    for res in Result.objects.filter(Q(challenge=challenge)):
        try:
            rank = ranks[str(res.pk)][score_path]
        except KeyError:
            # This result will be excluded from the display
            rank = 0

        Result.objects.filter(pk=res.pk).update(rank=rank)

    return ranks
