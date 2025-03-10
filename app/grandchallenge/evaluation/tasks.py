import logging
import uuid
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import OperationalError, transaction
from django.db.models import Case, IntegerField, Value, When
from django.db.transaction import on_commit
from django.utils.timezone import now

from grandchallenge.algorithms.exceptions import TooManyJobsScheduled
from grandchallenge.algorithms.models import AlgorithmModel, Job
from grandchallenge.algorithms.tasks import create_algorithm_jobs
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.evaluation.utils import rank_results

logger = logging.getLogger(__name__)


@acks_late_2xlarge_task
@transaction.atomic
def prepare_and_execute_evaluation(
    *, evaluation_pk, max_initial_jobs=1
):  # noqa: C901
    """
    Prepares an evaluation object for execution

    Parameters
    ----------
    evaluation_pk
        The primary key of the Evaluation
    max_initial_jobs
        The maximum number of algorithm jobs to schedule first
    """
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evaluation = Evaluation.objects.get(pk=evaluation_pk)
    submission = evaluation.submission

    if not evaluation.additional_inputs_complete:
        logger.info("Nothing to do, inputs are still being validated.")
        return

    if evaluation.status != evaluation.VALIDATING_INPUTS:
        # this task can be called multiple times with complete inputs,
        # and might have been queued for execution already, so ignore
        logger.info("Evaluation has already been scheduled for execution.")
        return

    if not submission.predictions_file and submission.user_upload:
        submission.user_upload.copy_object(
            to_field=submission.predictions_file
        )
        submission.user_upload.delete()

    if submission.algorithm_image:
        evaluation.status = Evaluation.PENDING
        evaluation.save()
        on_commit(
            lambda: create_algorithm_jobs_for_evaluation.apply_async(
                kwargs={
                    "evaluation_pk": evaluation_pk,
                    "max_jobs": max_initial_jobs,
                }
            )
        )
    elif submission.predictions_file:
        mimetype = get_file_mimetype(submission.predictions_file)

        if mimetype == "application/zip":
            interface = ComponentInterface.objects.get(
                slug="predictions-zip-file"
            )
        elif mimetype in ["text/plain", "application/csv", "text/csv"]:
            interface = ComponentInterface.objects.get(
                slug="predictions-csv-file"
            )
        else:
            evaluation.update_status(
                status=Evaluation.FAILURE,
                stderr=f"{mimetype} files are not supported.",
                error_message=f"{mimetype} files are not supported.",
            )
            return

        civ = ComponentInterfaceValue(
            interface=interface, file=submission.predictions_file
        )

        try:
            civ.full_clean()
        except ValidationError as e:
            evaluation.update_status(
                status=Evaluation.FAILURE, error_message=str(e)
            )
            return

        civ.save()
        evaluation.inputs.add(civ)
        evaluation.status = Evaluation.PENDING
        evaluation.save()
        on_commit(evaluation.execute)
    else:
        raise RuntimeError("No algorithm or predictions file found")


@acks_late_2xlarge_task(retry_on=(TooManyJobsScheduled,), singleton=True)
def create_algorithm_jobs_for_evaluation(*, evaluation_pk, max_jobs=1):
    """
    Creates the algorithm jobs for the evaluation

    By default the number of jobs are limited to allow for failures.
    Once this task is called without limits the remaining jobs are
    scheduled (if any), and the evaluation run.

    Parameters
    ----------
    evaluation_pk
        The primary key of the evaluation
    max_jobs
        The maximum number of jobs to create
    """
    if Job.objects.active().count() >= settings.ALGORITHMS_MAX_ACTIVE_JOBS:
        raise TooManyJobsScheduled

    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evaluation = Evaluation.objects.get(pk=evaluation_pk)

    if evaluation.status not in {
        evaluation.PENDING,
        evaluation.EXECUTING_PREREQUISITES,
    }:
        logger.info(
            f"Nothing to do: evaluation is {evaluation.get_status_display()}."
        )
        return

    # Only the challenge admins should be able to view these jobs, never
    # the algorithm editors as these are participants - they must never
    # be able to see the test data...
    viewer_groups = [evaluation.submission.phase.challenge.admins_group]

    # ...unless the challenge admins have opted in to this
    if evaluation.submission.phase.give_algorithm_editors_job_view_permissions:
        viewer_groups.append(
            evaluation.submission.algorithm_image.algorithm.editors_group
        )

    if max_jobs is None:
        # Once the algorithm has been run, score the submission. No emails as
        # algorithm editors should not have access to the underlying images.
        task_on_success = set_evaluation_inputs.signature(
            kwargs={"evaluation_pk": str(evaluation.pk)}, immutable=True
        )
    else:
        # Run with 1 job and then if that goes well, come back and
        # run all jobs. Note that setting None here is caught by
        # the if statement to schedule `set_evaluation_inputs`
        task_on_success = create_algorithm_jobs_for_evaluation.signature(
            kwargs={"evaluation_pk": str(evaluation.pk), "max_jobs": None},
            immutable=True,
        )

    # If any of the jobs fail then mark the evaluation as failed.
    task_on_failure = handle_failed_jobs.signature(
        kwargs={"evaluation_pk": str(evaluation.pk)}, immutable=True
    )

    evaluation.update_status(status=Evaluation.EXECUTING_PREREQUISITES)

    jobs = create_algorithm_jobs(
        algorithm_image=evaluation.submission.algorithm_image,
        algorithm_model=evaluation.submission.algorithm_model,
        archive_items=evaluation.submission.phase.archive.items.prefetch_related(
            "values__interface"
        )
        .annotate(
            has_title=Case(
                When(title="", then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("has_title", "title", "created"),
        extra_viewer_groups=viewer_groups,
        extra_logs_viewer_groups=viewer_groups,
        task_on_success=task_on_success,
        task_on_failure=task_on_failure,
        max_jobs=max_jobs,
        time_limit=evaluation.submission.phase.algorithm_time_limit,
        requires_gpu_type=evaluation.submission.algorithm_requires_gpu_type,
        requires_memory_gb=evaluation.submission.algorithm_requires_memory_gb,
    )

    if not jobs:
        # No more jobs created from this task, so everything must be
        # ready for evaluation, handles archives with only one item
        # and re-evaluation of existing submissions with new methods
        set_evaluation_inputs.signature(
            kwargs={"evaluation_pk": str(evaluation.pk)},
            immutable=True,
        ).apply_async()


@acks_late_micro_short_task
@transaction.atomic
def handle_failed_jobs(*, evaluation_pk):
    # Set the evaluation to failed
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evaluation = Evaluation.objects.get(pk=evaluation_pk)
    if evaluation.status != evaluation.FAILURE:
        evaluation.update_status(
            status=evaluation.FAILURE,
            error_message="The algorithm failed on one or more cases.",
        )

    # Cancel any pending jobs for this algorithm image,
    # we could limit by archive here but if non-evaluation
    # jobs are cancelled then it is no big loss.
    Job = apps.get_model(  # noqa: N806
        app_label="algorithms", model_name="Job"
    )
    Job.objects.filter(
        algorithm_image=evaluation.submission.algorithm_image,
        status__in=[Job.PENDING, Job.PROVISIONED, Job.RETRY],
    ).select_for_update(skip_locked=True).update(status=Job.CANCELLED)


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def set_evaluation_inputs(*, evaluation_pk):
    """
    Sets the inputs to the Evaluation for an algorithm submission.

    If all of the `Job`s for this algorithm `Submission` are
    successful this will set the inputs to the `Evaluation` job and schedule
    it. If any of the `Job`s are unsuccessful then the
    `Evaluation` will be marked as Failed.

    This task can take a while so place it on the large queue.

    Parameters
    ----------
    evaluation_pk
        The primary key of the evaluation.Evaluation object
    """
    Job = apps.get_model(  # noqa: N806
        app_label="algorithms", model_name="Job"
    )
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )

    if AlgorithmModel.objects.filter(
        submission__evaluation=evaluation_pk
    ).exists():
        pending_jobs_extra_filter = {
            "algorithm_model__submission__evaluation": evaluation_pk
        }
    else:
        pending_jobs_extra_filter = {"algorithm_model__isnull": True}

    has_pending_jobs = (
        Job.objects.active()
        .filter(
            algorithm_image__submission__evaluation=evaluation_pk,
            creator__isnull=True,  # Evaluation inference jobs have no creator
            **pending_jobs_extra_filter,
        )
        .exists()
    )

    if has_pending_jobs:
        logger.info("Nothing to do: the algorithm has pending jobs.")
        return

    evaluation_queryset = Evaluation.objects.filter(
        pk=evaluation_pk
    ).select_for_update(nowait=True)

    try:
        # Acquire lock
        evaluation = evaluation_queryset.get()
    except OperationalError as error:
        raise LockNotAcquiredException from error

    if evaluation.status != evaluation.EXECUTING_PREREQUISITES:
        logger.info(
            f"Nothing to do: evaluation is {evaluation.get_status_display()}."
        )
        return

    if evaluation.inputs_complete:
        from grandchallenge.algorithms.serializers import JobSerializer
        from grandchallenge.components.models import (
            ComponentInterface,
            ComponentInterfaceValue,
        )

        serializer = JobSerializer(evaluation.successful_jobs.all(), many=True)
        interface = ComponentInterface.objects.get(
            slug="predictions-json-file"
        )
        civ = ComponentInterfaceValue.objects.create(
            interface=interface, value=serializer.data
        )

        output_to_job = {
            o.pk: j.pk
            for j in evaluation.successful_jobs.all()
            for o in j.outputs.all()
        }

        evaluation.inputs.add(*[civ.pk, *output_to_job.keys()])
        evaluation.input_prefixes = {
            str(o): f"{j}/output/" for o, j in output_to_job.items()
        }
        evaluation.status = Evaluation.PENDING
        evaluation.save()

        on_commit(evaluation.execute)


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


# Use 2xlarge for memory use
@acks_late_2xlarge_task(
    retry_on=(LockNotAcquiredException,), delayed_retry=False
)
@transaction.atomic
def calculate_ranks(*, phase_pk: uuid.UUID):
    Phase = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Phase"
    )
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )

    phase = Phase.objects.get(pk=phase_pk)

    try:
        # Acquire locks
        evaluations = list(
            Evaluation.objects.filter(
                submission__phase=phase,
                status=Evaluation.SUCCESS,
            )
            .select_for_update(nowait=True, of=("self",))
            .order_by("-created")
            .select_related("submission__creator", "submission__phase")
            .prefetch_related("outputs__interface")
        )
    except OperationalError as error:
        raise LockNotAcquiredException from error

    valid_evaluations = [
        e
        for e in evaluations
        if e.status == Evaluation.SUCCESS and e.published is True
    ]

    if phase.result_display_choice == phase.MOST_RECENT:
        valid_evaluations = filter_by_creators_most_recent(
            evaluations=valid_evaluations
        )
    elif phase.result_display_choice == phase.BEST:
        all_positions = rank_results(
            evaluations=valid_evaluations,
            metrics=phase.valid_metrics,
            score_method=phase.scoring_method,
        )
        valid_evaluations = filter_by_creators_best(
            evaluations=valid_evaluations, ranks=all_positions.ranks
        )

    final_positions = rank_results(
        evaluations=valid_evaluations,
        metrics=phase.valid_metrics,
        score_method=phase.scoring_method,
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

    for leaderboard in phase.combinedleaderboard_set.all():
        leaderboard.schedule_combined_ranks_update()


@acks_late_2xlarge_task
@transaction.atomic
def update_combined_leaderboard(*, pk):
    CombinedLeaderboard = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="CombinedLeaderboard"
    )

    leaderboard = CombinedLeaderboard.objects.get(pk=pk)
    leaderboard.update_combined_ranks_cache()


@acks_late_2xlarge_task
@transaction.atomic
def assign_evaluation_permissions(*, phase_pks: uuid.UUID):
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evals = Evaluation.objects.filter(
        submission__phase__id__in=phase_pks,
    )

    for e in evals:
        e.assign_permissions()


@acks_late_2xlarge_task
@transaction.atomic
def assign_submission_permissions(*, phase_pk: uuid.UUID):
    Submission = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Submission"
    )
    for sub in Submission.objects.filter(phase__id=phase_pk):
        sub.assign_permissions()


@acks_late_micro_short_task
@transaction.atomic
def cancel_external_evaluations_past_timeout():
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    timeout_threshold = now() - timedelta(
        seconds=settings.EXTERNAL_EVALUATION_TIMEOUT_IN_SECONDS
    )

    for eval in Evaluation.objects.filter(
        status=Evaluation.CLAIMED,
        started_at__lt=timeout_threshold,
    ).all():
        eval.update_status(
            status=Evaluation.CANCELLED,
            error_message="External evaluation timed out.",
            compute_cost_euro_millicents=0,
        )
