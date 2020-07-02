import uuid
from statistics import mean, median

from celery import shared_task

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Config, Job
from grandchallenge.evaluation.utils import Metric, rank_results


def filter_by_creators_most_recent(*, jobs):
    # Go through the jobs and only pass through the most recent
    # submission for each user
    users_seen = set()
    filtered_qs = []

    for j in jobs:
        creator = j.submission.creator

        if creator not in users_seen:
            users_seen.add(creator)
            filtered_qs.append(j)

    return filtered_qs


def filter_by_creators_best(*, jobs, ranks):
    best_result_per_user = {}

    for j in jobs:
        creator = j.submission.creator

        try:
            this_rank = ranks[j.pk]
        except KeyError:
            # This result was not ranked
            continue

        if creator not in best_result_per_user or (
            this_rank < ranks[best_result_per_user[creator].pk]
        ):
            best_result_per_user[creator] = j

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

    valid_jobs = (
        Job.objects.filter(submission__challenge=challenge, published=True)
        .order_by("-created")
        .select_related("submission")
    )

    if display_choice == Config.MOST_RECENT:
        valid_jobs = filter_by_creators_most_recent(jobs=valid_jobs)
    elif display_choice == Config.BEST:
        all_positions = rank_results(
            jobs=valid_jobs, metrics=metrics, score_method=score_method
        )
        valid_jobs = filter_by_creators_best(
            jobs=valid_jobs, ranks=all_positions.ranks
        )

    final_positions = rank_results(
        jobs=valid_jobs, metrics=metrics, score_method=score_method
    )

    for j in Job.objects.filter(submission__challenge=challenge):
        try:
            rank = final_positions.ranks[j.pk]
            rank_score = final_positions.rank_scores[j.pk]
            rank_per_metric = final_positions.rank_per_metric[j.pk]
        except KeyError:
            # This result will be excluded from the display
            rank = 0
            rank_score = 0.0
            rank_per_metric = {}

        Job.objects.filter(pk=j.pk).update(
            rank=rank, rank_score=rank_score, rank_per_metric=rank_per_metric
        )
