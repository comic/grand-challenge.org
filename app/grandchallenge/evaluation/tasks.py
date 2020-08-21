import uuid
from statistics import mean, median

from celery import shared_task
from django.apps import apps

from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.evaluation.utils import Metric, rank_results


@shared_task
def set_evaluation_inputs(*_, evaluation_pk):
    """
    Sets the inputs to the Evaluation for a algorithm submission.

    If all of the `AlgorithmEvaluation`s for this algorithm `Submission` are
    successful this will set the inputs to the `Evaluation` job and schedule
    it. If any of the `AlgorithmEvaluation`s are unsuccessful then the
    `Evaluation` will be marked as Failed.

    Parameters
    ----------
    evaluation_pk
        The primary key of the evaluation.Evaluation object
    """
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )

    evaluation = Evaluation.objects.get(pk=evaluation_pk)

    unsuccessful_jobs = evaluation.submission.algorithmevaluation_set.exclude(
        status=Evaluation.SUCCESS
    ).count()

    if unsuccessful_jobs:
        evaluation.update_status(
            status=evaluation.FAILURE,
            output=(
                f"The algorithm failed to execute on {unsuccessful_jobs} "
                f"images."
            ),
        )
    else:
        evaluation.inputs.set(
            ComponentInterfaceValue.objects.filter(
                evaluation_algorithmevaluations_as_output__submission=evaluation.submission
            )
        )
        evaluation.signature.apply_async()


def filter_by_creators_most_recent(*, evaluations):
    # Go through the evaluations and only pass through the most recent
    # submission for each user
    users_seen = set()
    filtered_qs = []

    for e in evaluations:
        creator = e.submission.creator

        if creator not in users_seen:
            users_seen.add(creator)
            filtered_qs.append(e)

    return filtered_qs


def filter_by_creators_best(*, evaluations, ranks):
    best_result_per_user = {}

    for e in evaluations:
        creator = e.submission.creator

        try:
            this_rank = ranks[e.pk]
        except KeyError:
            # This result was not ranked
            continue

        if creator not in best_result_per_user or (
            this_rank < ranks[best_result_per_user[creator].pk]
        ):
            best_result_per_user[creator] = e

    return [r for r in best_result_per_user.values()]


@shared_task  # noqa: C901
def calculate_ranks(*, challenge_pk: uuid.UUID):  # noqa: C901
    challenge = Challenge.objects.get(pk=challenge_pk)
    display_choice = challenge.evaluation_config.result_display_choice
    score_method_choice = challenge.evaluation_config.scoring_method_choice

    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )

    metrics = (
        Metric(
            path=challenge.evaluation_config.score_jsonpath,
            reverse=(
                challenge.evaluation_config.score_default_sort
                == challenge.evaluation_config.DESCENDING
            ),
        ),
        *[
            Metric(
                path=col["path"],
                reverse=col["order"] == challenge.evaluation_config.DESCENDING,
            )
            for col in challenge.evaluation_config.extra_results_columns
        ],
    )

    if score_method_choice == challenge.evaluation_config.ABSOLUTE:

        def score_method(x):
            return list(x)[0]

    elif score_method_choice == challenge.evaluation_config.MEAN:
        score_method = mean
    elif score_method_choice == challenge.evaluation_config.MEDIAN:
        score_method = median
    else:
        raise NotImplementedError

    valid_evaluations = (
        Evaluation.objects.filter(
            submission__challenge=challenge,
            published=True,
            status=Evaluation.SUCCESS,
        )
        .order_by("-created")
        .select_related("submission__creator")
        .prefetch_related("outputs__interface")
    )

    if display_choice == challenge.evaluation_config.MOST_RECENT:
        valid_evaluations = filter_by_creators_most_recent(
            evaluations=valid_evaluations
        )
    elif display_choice == challenge.evaluation_config.BEST:
        all_positions = rank_results(
            evaluations=valid_evaluations,
            metrics=metrics,
            score_method=score_method,
        )
        valid_evaluations = filter_by_creators_best(
            evaluations=valid_evaluations, ranks=all_positions.ranks
        )

    final_positions = rank_results(
        evaluations=valid_evaluations,
        metrics=metrics,
        score_method=score_method,
    )

    evaluations = Evaluation.objects.filter(submission__challenge=challenge)

    _update_evaluations(
        evaluations=evaluations, final_positions=final_positions
    )


def _update_evaluations(*, evaluations, final_positions):
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )

    for e in evaluations:
        try:
            rank = final_positions.ranks[e.pk]
            rank_score = final_positions.rank_scores[e.pk]
            rank_per_metric = final_positions.rank_per_metric[e.pk]
        except KeyError:
            # This result will be excluded from the display
            rank = 0
            rank_score = 0.0
            rank_per_metric = {}

        e.rank = rank
        e.rank_score = rank_score
        e.rank_per_metric = rank_per_metric

    Evaluation.objects.bulk_update(
        evaluations, ["rank", "rank_score", "rank_per_metric"]
    )
