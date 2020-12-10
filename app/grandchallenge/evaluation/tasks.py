import uuid
from statistics import mean, median

from celery import shared_task
from django.apps import apps

from grandchallenge.evaluation.utils import Metric, rank_results


@shared_task
def set_evaluation_inputs(evaluation_pk, job_pks):
    """
    Sets the inputs to the Evaluation for a algorithm submission.

    If all of the `Job`s for this algorithm `Submission` are
    successful this will set the inputs to the `Evaluation` job and schedule
    it. If any of the `Job`s are unsuccessful then the
    `Evaluation` will be marked as Failed.

    Parameters
    ----------
    evaluation_pk
        The primary key of the evaluation.Evaluation object
    """
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    Job = apps.get_model(  # noqa: N806
        app_label="algorithms", model_name="Job"
    )

    evaluation = Evaluation.objects.get(pk=evaluation_pk)

    unsuccessful_jobs = (
        Job.objects.filter(pk__in=job_pks).exclude(status=Job.SUCCESS).count()
    )

    if unsuccessful_jobs:
        evaluation.update_status(
            status=evaluation.FAILURE,
            error_message=(
                f"The algorithm failed to execute on {unsuccessful_jobs} "
                f"images."
            ),
        )
    else:
        from grandchallenge.algorithms.serializers import JobSerializer
        from grandchallenge.components.models import (
            ComponentInterface,
            ComponentInterfaceValue,
        )

        serializer = JobSerializer(
            Job.objects.filter(pk__in=job_pks).all(), many=True
        )
        interface = ComponentInterface.objects.get(
            title="Predictions JSON File"
        )
        civ = ComponentInterfaceValue.objects.create(
            interface=interface, value=serializer.data
        )

        evaluation.inputs.set([civ])
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
def calculate_ranks(*, phase_pk: uuid.UUID):  # noqa: C901
    Phase = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Phase"
    )
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )

    phase = Phase.objects.get(pk=phase_pk)
    display_choice = phase.result_display_choice
    score_method_choice = phase.scoring_method_choice

    metrics = (
        Metric(
            path=phase.score_jsonpath,
            reverse=(phase.score_default_sort == phase.DESCENDING),
        ),
        *[
            Metric(path=col["path"], reverse=col["order"] == phase.DESCENDING,)
            for col in phase.extra_results_columns
        ],
    )

    if score_method_choice == phase.ABSOLUTE:

        def score_method(x):
            return list(x)[0]

    elif score_method_choice == phase.MEAN:
        score_method = mean
    elif score_method_choice == phase.MEDIAN:
        score_method = median
    else:
        raise NotImplementedError

    valid_evaluations = (
        Evaluation.objects.filter(
            submission__phase=phase, published=True, status=Evaluation.SUCCESS,
        )
        .order_by("-created")
        .select_related("submission__creator")
        .prefetch_related("outputs__interface")
    )

    if display_choice == phase.MOST_RECENT:
        valid_evaluations = filter_by_creators_most_recent(
            evaluations=valid_evaluations
        )
    elif display_choice == phase.BEST:
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

    evaluations = Evaluation.objects.filter(submission__phase=phase)

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


@shared_task
def assign_evaluation_permissions(*, challenge_pk: uuid.UUID):
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )

    for e in Evaluation.objects.filter(
        submission__phase__challenge__id=challenge_pk
    ):
        e.assign_permissions()
