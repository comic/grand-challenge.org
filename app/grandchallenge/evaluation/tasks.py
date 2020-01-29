import uuid
from statistics import mean, median

from celery import shared_task
from django.db.models import Q

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Config, Result
from grandchallenge.evaluation.utils import Metric, rank_results


def filter_by_creators_most_recent(*, results):
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


def filter_by_creators_best(*, results, ranks):
    best_result_per_user = {}

    for r in results:
        creator = r.job.submission.creator

        try:
            this_rank = ranks[r.pk]
        except KeyError:
            # This result was not ranked
            continue

        if creator not in best_result_per_user or (
            this_rank < ranks[best_result_per_user[creator].pk]
        ):
            best_result_per_user[creator] = r

    return [r for r in best_result_per_user.values()]


@shared_task  # noqa: C901
def calculate_ranks(*, challenge_pk: uuid.UUID):  # noqa: C901
    challenge = Challenge.objects.get(pk=challenge_pk)
    display_choice = challenge.evaluation_config.result_display_choice
    score_method_choice = challenge.evaluation_config.scoring_method_choice

    metrics = (
        Metric(
            path=challenge.evaluation_config.score_jsonpath,
            reverse=(
                challenge.evaluation_config.score_default_sort
                == Config.DESCENDING
            ),
        ),
    )

    if score_method_choice != Config.ABSOLUTE:
        metrics += tuple(
            Metric(path=col["path"], reverse=col["order"] == Config.DESCENDING)
            for col in challenge.evaluation_config.extra_results_columns
        )

    if score_method_choice == Config.ABSOLUTE and len(metrics) == 1:

        def score_method(x):
            return list(x)[0]

    elif score_method_choice == Config.MEAN:
        score_method = mean
    elif score_method_choice == Config.MEDIAN:
        score_method = median
    else:
        raise NotImplementedError

    valid_results = (
        Result.objects.filter(
            Q(job__submission__challenge=challenge), Q(published=True)
        )
        .order_by("-created")
        .select_related("job__submission")
    )

    if display_choice == Config.MOST_RECENT:
        valid_results = filter_by_creators_most_recent(results=valid_results)
    elif display_choice == Config.BEST:
        all_positions = rank_results(
            results=valid_results, metrics=metrics, score_method=score_method
        )
        valid_results = filter_by_creators_best(
            results=valid_results, ranks=all_positions.ranks
        )

    final_positions = rank_results(
        results=valid_results, metrics=metrics, score_method=score_method
    )

    for res in Result.objects.filter(Q(job__submission__challenge=challenge)):
        try:
            rank = final_positions.ranks[res.pk]
            rank_score = final_positions.rank_scores[res.pk]
            rank_per_metric = final_positions.rank_per_metric[res.pk]
        except KeyError:
            # This result will be excluded from the display
            rank = 0
            rank_score = 0.0
            rank_per_metric = {}

        Result.objects.filter(pk=res.pk).update(
            rank=rank, rank_score=rank_score, rank_per_metric=rank_per_metric
        )
