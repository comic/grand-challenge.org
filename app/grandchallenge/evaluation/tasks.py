import uuid
from datetime import timedelta

from celery.utils.log import get_task_logger
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
from grandchallenge.components.tasks import (
    check_operational_error,
    lock_for_utilization_update,
    lock_model_instance,
)
from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.evaluation.utils import SubmissionKindChoices, rank_results

logger = get_task_logger(__name__)


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def check_prerequisites_for_evaluation_execution(*, evaluation_pk):
    from grandchallenge.evaluation.models import (
        get_archive_items_for_interfaces,
        get_valid_jobs_for_interfaces_and_archive_items,
    )

    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evaluation = lock_model_instance(
        app_label="evaluation", model_name="evaluation", pk=evaluation_pk
    )
    submission = evaluation.submission

    if evaluation.status != evaluation.VALIDATING_INPUTS:
        # the evaluation might have been queued for execution already, so ignore
        logger.info("Evaluation has already been scheduled for execution.")
        return

    if submission.phase.submission_kind == SubmissionKindChoices.ALGORITHM:
        algorithm_interfaces = submission.phase.algorithm_interfaces.all()

        items = get_archive_items_for_interfaces(
            algorithm_interfaces=algorithm_interfaces,
            archive_items=submission.phase.archive.items.all(),
        )
        non_success_statuses = [
            status[0]
            for status in Job.STATUS_CHOICES
            if status[0] != Job.SUCCESS
        ]

        jobs = get_valid_jobs_for_interfaces_and_archive_items(
            algorithm_image=submission.algorithm_image,
            algorithm_model=submission.algorithm_model,
            algorithm_interfaces=algorithm_interfaces,
            valid_archive_items_per_interface=items,
            subset_by_status=non_success_statuses,
        )
    else:
        # prediction submissions never have blocking jobs
        jobs = {}

    if any(jobs.values()):
        evaluation.update_status(
            status=Evaluation.CANCELLED,
            error_message="There are non-successful jobs for this submission. "
            "These need to be handled first before you can "
            "re-evaluate. Please contact support.",
        )
        return
    else:
        e = prepare_and_execute_evaluation.signature(
            kwargs={"evaluation_pk": evaluation.pk}, immutable=True
        )
        on_commit(e.apply_async)


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def prepare_and_execute_evaluation(*, evaluation_pk):  # noqa: C901
    """
    Prepares an evaluation object for execution

    Parameters
    ----------
    evaluation_pk
        The primary key of the Evaluation
    """
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evaluation = lock_model_instance(
        app_label="evaluation", model_name="Evaluation", pk=evaluation_pk
    )
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
        evaluation.status = Evaluation.EXECUTING_PREREQUISITES
        evaluation.save()
        on_commit(
            lambda: create_algorithm_jobs_for_evaluation.apply_async(
                kwargs={
                    "evaluation_pk": evaluation_pk,
                    "first_run": True,
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
        evaluation.update_status(
            status=Evaluation.FAILURE,
            error_message="An unexpected error occurred",
        )
        logger.error("No algorithm or predictions file found")


@acks_late_micro_short_task(
    retry_on=(TooManyJobsScheduled, LockNotAcquiredException)
)
@transaction.atomic
def create_algorithm_jobs_for_evaluation(*, evaluation_pk, first_run):
    """
    Creates the algorithm jobs for the evaluation

    By default the number of jobs are limited to allow for failures.
    Once this task is called without limits the remaining jobs are
    scheduled (if any), and the evaluation run.

    Parameters
    ----------
    evaluation_pk
        The primary key of the evaluation
    first_run
        Whether this is the first run of create_algorithm_jobs_for_evaluation
    """
    evaluation = lock_model_instance(
        pk=evaluation_pk,
        app_label="evaluation",
        model_name="Evaluation",
        select_related=("submission",),
        of=("self",),
    )

    if evaluation.status != evaluation.EXECUTING_PREREQUISITES:
        logger.info(
            f"Nothing to do: evaluation is {evaluation.get_status_display()}."
        )
        return

    lock_for_utilization_update(
        algorithm_image_pk=evaluation.submission.algorithm_image_id
    )

    slots_available = min(
        settings.ALGORITHMS_MAX_ACTIVE_JOBS - Job.objects.active().count(),
        settings.ALGORITHMS_MAX_ACTIVE_JOBS_PER_ALGORITHM,
    )
    slots_available -= (
        Job.objects.active()
        .filter(algorithm_image=evaluation.submission.algorithm_image)
        .count()
    )

    if slots_available <= 0:
        raise TooManyJobsScheduled

    # Only the challenge admins should be able to view these jobs, never
    # the algorithm editors as these are participants - they must never
    # be able to see the test data...
    viewer_groups = [evaluation.submission.phase.challenge.admins_group]

    # ...unless the challenge admins have opted in to this
    if evaluation.submission.phase.give_algorithm_editors_job_view_permissions:
        viewer_groups.append(
            evaluation.submission.algorithm_image.algorithm.editors_group
        )

    if first_run:
        # Run with 1 job and then if that goes well, come back and
        # run all jobs.
        task_on_success = create_algorithm_jobs_for_evaluation.signature(
            kwargs={"evaluation_pk": str(evaluation.pk), "first_run": False},
            immutable=True,
        )
        max_jobs = 1
    else:
        # Once the algorithm has been run, score the submission. No emails as
        # algorithm editors should not have access to the underlying images.
        task_on_success = set_evaluation_inputs.signature(
            kwargs={"evaluation_pk": str(evaluation.pk)}, immutable=True
        )
        max_jobs = slots_available

    # If any of the jobs fail then mark the evaluation as failed.
    task_on_failure = handle_failed_jobs.signature(
        kwargs={"evaluation_pk": str(evaluation.pk)}, immutable=True
    )

    try:
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
            job_utilization_phase=evaluation.submission.phase,
            job_utilization_challenge=evaluation.submission.phase.challenge,
        )
    except TooManyJobsScheduled:
        if not first_run:
            # Manually create the retry task so that the jobs
            # created above are committed
            create_algorithm_jobs_for_evaluation._retry()
        return

    if not jobs:
        # No more jobs created from this task, so everything must be
        # ready for evaluation, handles archives with only one item
        # and re-evaluation of existing submissions with new methods
        on_commit(
            set_evaluation_inputs.signature(
                kwargs={"evaluation_pk": str(evaluation.pk)},
                immutable=True,
            ).apply_async
        )


@acks_late_micro_short_task(
    retry_on=(LockNotAcquiredException,), delayed_retry=False
)
@transaction.atomic
def handle_failed_jobs(*, evaluation_pk):
    # Set the evaluation to failed
    evaluation = lock_model_instance(
        pk=evaluation_pk,
        app_label="evaluation",
        model_name="Evaluation",
        select_related=("submission",),
        of=("self",),
    )

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

    try:
        Job.objects.filter(
            creator=None,
            algorithm_image_id=evaluation.submission.algorithm_image_id,
            status__in=[Job.PENDING, Job.PROVISIONED, Job.RETRY],
        ).select_for_update(of=("self",), skip_locked=True).update(
            status=Job.CANCELLED
        )
    except OperationalError as error:
        check_operational_error(error)
        raise


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
    evaluation = lock_model_instance(
        pk=evaluation_pk, app_label="evaluation", model_name="Evaluation"
    )

    if evaluation.status != evaluation.EXECUTING_PREREQUISITES:
        logger.info(
            f"Nothing to do: evaluation is {evaluation.get_status_display()}."
        )
        return

    Job = apps.get_model(  # noqa: N806
        app_label="algorithms", model_name="Job"
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
        evaluation.status = evaluation.PENDING
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
        check_operational_error(error)
        raise

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
        claimed_at__lt=timeout_threshold,
    ).all():
        eval.update_status(
            status=Evaluation.CANCELLED,
            error_message="External evaluation timed out.",
            compute_cost_euro_millicents=0,
        )
