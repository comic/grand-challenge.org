import uuid

from celery import shared_task
from django.db.models import Q

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Result, Config
from grandchallenge.evaluation.utils import generate_ranks


def filter_results_by_most_recent(*, results):
    # Go through the results and only pass through the most recent
    # submission for each user
    users_seen = set()
    filtered_qs = []

    for r in results:
        creator = r.job.submission.creator

        if creator not in users_seen:
            users_seen.add(creator)
            filtered_qs.append(r)

    return filtered_qs


def filter_results_by_users_best(*, results, ranks):

    best_result_per_user = {}

    for r in results:
        creator = r.job.submission.creator

        try:
            this_rank = ranks[str(r.pk)]
        except KeyError:
            # This result was not ranked
            continue

        if creator not in best_result_per_user or (
            this_rank < ranks[str(best_result_per_user[creator].pk)]
        ):
            best_result_per_user[creator] = r

    return [r for r in best_result_per_user.values()]


@shared_task
def calculate_ranks(*, challenge_pk: uuid.UUID):
    challenge = Challenge.objects.get(pk=challenge_pk)
    display_choice = challenge.evaluation_config.result_display_choice

    metric_paths = (challenge.evaluation_config.score_jsonpath,)
    metric_reverse = (
        challenge.evaluation_config.score_default_sort == Config.DESCENDING,
    )

    valid_results = (
        Result.objects.filter(Q(challenge=challenge), Q(published=True))
        .order_by("-created")
        .select_related("job__submission")
    )

    if display_choice == Config.MOST_RECENT:
        queryset = filter_results_by_most_recent(results=valid_results)
    elif display_choice == Config.BEST:
        queryset = filter_results_by_users_best(
            results=valid_results,
            ranks=generate_ranks(
                queryset=valid_results,
                metric_paths=metric_paths,
                metric_reverse=metric_reverse,
            ),
        )
    else:
        queryset = valid_results

    ranks = generate_ranks(
        queryset=queryset,
        metric_paths=metric_paths,
        metric_reverse=metric_reverse,
    )

    for res in Result.objects.filter(Q(challenge=challenge)):
        try:
            rank = ranks[str(res.pk)]
        except KeyError:
            # This result will be excluded from the display
            rank = 0

        Result.objects.filter(pk=res.pk).update(rank=rank)

    return ranks
