import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task
from lambda_tasks.logging import task_logger

from config.lambda_tasks import (
    LONG_TASK_HARD_TIMEOUT,
    LONG_TASK_SOFT_TIMEOUT,
    LambdaTaskQueueChoices,
)
from grandchallenge.algorithms.exceptions import TooManyJobsScheduled
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.tasks import lock_for_utilization_update
from grandchallenge.core.error_messages import (
    EvaluationErrorMessages,
    SystemErrorMessages,
)
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.utils.query import check_lock_acquired
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.evaluation.utils import SubmissionKindChoices, rank_results


@lambda_task(retry_on=(LockNotAcquiredException,))
def check_prerequisites_for_evaluation_execution(
    *, evaluation_pk: str | uuid.UUID
):
    from grandchallenge.evaluation.models import Evaluation

    with check_lock_acquired():
        evaluation = (
            Evaluation.objects.select_related(
                "submission",
                "submission__algorithm_image",
                "submission__algorithm_model",
            )
            .prefetch_related(
                "submission__phase__archive__items",
                "submission__phase__algorithm_interfaces",
            )
            .select_for_update(nowait=True, of=("self",))
            .get(pk=evaluation_pk)
        )

    if evaluation.status != evaluation.VALIDATING_INPUTS:
        # the evaluation might have been queued for execution already, so ignore
        task_logger.info(
            "Evaluation has already been scheduled for execution."
        )
        return

    if (
        evaluation.submission.phase.submission_kind
        == SubmissionKindChoices.ALGORITHM
    ):
        blocking_inference_tasks_per_interface = (
            evaluation.blocking_inference_tasks_per_interface
        )
    else:
        # prediction submissions never have blocking inference tasks
        blocking_inference_tasks_per_interface = {}

    if any(blocking_inference_tasks_per_interface.values()):
        evaluation.update_status(
            status=Evaluation.CANCELLED,
            error_message=EvaluationErrorMessages.UNSUCCESSFUL_JOBS,
        )
        return
    else:
        prepare_and_execute_evaluation.execute_on_commit(
            evaluation_pk=evaluation.pk
        )


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G, retry_on=(LockNotAcquiredException,)
)
def prepare_and_execute_evaluation(*, evaluation_pk: str | uuid.UUID):
    """
    Prepares an evaluation object for execution

    Parameters
    ----------
    evaluation_pk
        The primary key of the Evaluation
    """
    from grandchallenge.evaluation.models import Evaluation

    with check_lock_acquired():
        evaluation = (
            Evaluation.objects.select_related(
                "submission",
                "submission__algorithm_image",
                "submission__user_upload",
            )
            .select_for_update(nowait=True, of=("self",))
            .get(pk=evaluation_pk)
        )

    if not evaluation.additional_inputs_complete:
        task_logger.info("Nothing to do, inputs are still being validated.")
        return

    if evaluation.status != evaluation.VALIDATING_INPUTS:
        # this task can be called multiple times with complete inputs,
        # and might have been queued for execution already, so ignore
        task_logger.info(
            "Evaluation has already been scheduled for execution."
        )
        return

    if (
        not evaluation.submission.predictions_file
        and evaluation.submission.user_upload
    ):
        evaluation.submission.user_upload.copy_object(
            to_field=evaluation.submission.predictions_file
        )
        evaluation.submission.user_upload.delete()

    if evaluation.submission.algorithm_image:
        evaluation.status = Evaluation.PENDING
        evaluation.save()
        create_algorithm_jobs_for_evaluation.execute_on_commit(
            evaluation_pk=evaluation_pk,
            first_run=True,
        )
    elif evaluation.submission.predictions_file:
        mimetype = get_file_mimetype(evaluation.submission.predictions_file)

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
                error_message=EvaluationErrorMessages.UNSUPPORTED_INPUT,
            )
            return

        civ = ComponentInterfaceValue(
            interface=interface, file=evaluation.submission.predictions_file
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

        evaluation.execute()
    else:
        evaluation.update_status(
            status=Evaluation.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )
        task_logger.error("No algorithm or predictions file found")


@lambda_task(
    retry_on=(TooManyJobsScheduled, LockNotAcquiredException),
    retry_delay=60,
)
def create_algorithm_jobs_for_evaluation(
    *, evaluation_pk: str | uuid.UUID, first_run: bool
):
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
    from grandchallenge.evaluation.models import (
        Evaluation,
        active_inference_jobs_count,
    )

    with check_lock_acquired():
        evaluation = (
            Evaluation.objects.select_related("submission__creator")
            .select_for_update(nowait=True, of=("self",))
            .get(pk=evaluation_pk)
        )

    expected_status = (
        evaluation.PENDING if first_run else evaluation.EXECUTING_PREREQUISITES
    )

    if evaluation.status != expected_status:
        task_logger.info(
            f"Nothing to do: evaluation {first_run=} is {evaluation.get_status_display()}."
        )
        return

    lock_for_utilization_update(
        algorithm_image_pk=evaluation.submission.algorithm_image_id,
        invoice_pk=evaluation.utilization.invoice_id,
    )

    slots_available = min(
        settings.ALGORITHMS_MAX_ACTIVE_JOBS - active_inference_jobs_count(),
        settings.ALGORITHMS_MAX_ACTIVE_JOBS_PER_ALGORITHM,
    )
    slots_available -= active_inference_jobs_count(
        algorithm_image=evaluation.submission.algorithm_image
    )

    if slots_available <= 0:
        raise TooManyJobsScheduled

    if first_run:
        # Only go ahead if this is the users only active evaluation to
        # prevent flooding of the system
        user_has_other_active_evaluations = (
            Evaluation.objects.filter(
                submission__creator=evaluation.submission.creator,
                status=Evaluation.EXECUTING_PREREQUISITES,
            )
            .exclude(pk=evaluation.pk)
            .exists()
        )

        if user_has_other_active_evaluations:
            task_logger.info(
                "Nothing to do: user has other active evaluations."
            )
            raise TooManyJobsScheduled
        else:
            evaluation.status = Evaluation.EXECUTING_PREREQUISITES
            evaluation.save()

        # Run with 1 job and then if that goes well, come back and
        # run all jobs.
        task_on_success = create_algorithm_jobs_for_evaluation.serialize(
            evaluation_pk=evaluation.pk,
            first_run=False,
        )
        max_jobs = 1
    else:
        # Once the algorithm has been run, score the submission. No emails as
        # algorithm editors should not have access to the underlying images.
        task_on_success = set_evaluation_inputs.serialize(
            evaluation_pk=evaluation.pk
        )
        max_jobs = slots_available

    # If any of the jobs fail then mark the evaluation as failed.
    task_on_failure = handle_failed_jobs.serialize(evaluation_pk=evaluation.pk)

    try:
        jobs = evaluation.submission.create_inference_jobs(
            max_jobs=max_jobs,
            task_on_success=task_on_success,
            task_on_failure=task_on_failure,
            job_utilization_invoice=evaluation.utilization.invoice,
        )
    except TooManyJobsScheduled:
        if not first_run:
            # Manually create the retry task so that the jobs
            # created above are committed
            create_algorithm_jobs_for_evaluation.execute_on_commit(
                evaluation_pk=evaluation.pk, first_run=first_run, _delay=60
            )
        return

    if not jobs:
        # No more jobs created from this task, so everything must be
        # ready for evaluation, handles archives with only one item
        # and re-evaluation of existing submissions with new methods
        set_evaluation_inputs.execute_on_commit(evaluation_pk=evaluation.pk)


@lambda_task(retry_on=(LockNotAcquiredException,))
def handle_failed_jobs(*, evaluation_pk: str | uuid.UUID):
    from grandchallenge.evaluation.models import Evaluation

    with check_lock_acquired():
        evaluation = (
            Evaluation.objects.select_related("submission")
            .select_for_update(nowait=True, of=("self",))
            .get(pk=evaluation_pk)
        )

    if evaluation.status != evaluation.FAILURE:
        evaluation.update_status(
            status=evaluation.FAILURE,
            error_message=EvaluationErrorMessages.ALGORITHM_FAILURE,
        )

    evaluation.cancel_pending_inference_jobs()


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G,
    retry_on=(LockNotAcquiredException,),
    soft_timeout=LONG_TASK_SOFT_TIMEOUT,
    hard_timeout=LONG_TASK_HARD_TIMEOUT,
)
def set_evaluation_inputs(*, evaluation_pk: str | uuid.UUID):
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
    from grandchallenge.evaluation.models import Evaluation

    with check_lock_acquired():
        evaluation = Evaluation.objects.select_for_update(nowait=True).get(
            pk=evaluation_pk
        )

    if evaluation.status != evaluation.EXECUTING_PREREQUISITES:
        task_logger.info(
            f"Nothing to do: evaluation is {evaluation.get_status_display()}."
        )
        return

    if evaluation.has_pending_inference_jobs:
        task_logger.info("Nothing to do: the algorithm has pending jobs.")
        return

    if evaluation.inputs_complete:
        from grandchallenge.components.models import (
            ComponentInterface,
            ComponentInterfaceValue,
        )

        successful_inference_tasks = evaluation.successful_inference_tasks
        serializer = evaluation.job_serializer_class(
            successful_inference_tasks, many=True
        )
        output_to_inference_task = {
            output.pk: inference_task.pk
            for inference_task in successful_inference_tasks
            for output in inference_task.outputs.all()
        }

        interface = ComponentInterface.objects.get(
            slug="predictions-json-file"
        )
        civ = ComponentInterfaceValue.objects.create(
            interface=interface, value=serializer.data
        )

        evaluation.inputs.add(*[civ.pk, *output_to_inference_task.keys()])
        evaluation.input_prefixes = {
            str(output_pk): f"{inference_task_pk}/output/"
            for output_pk, inference_task_pk in (
                output_to_inference_task.items()
            )
        }
        evaluation.status = evaluation.PENDING
        evaluation.save()

        evaluation.execute()


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


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G,
    retry_on=(LockNotAcquiredException,),
)
def calculate_ranks(*, phase_pk: str | uuid.UUID):
    from grandchallenge.evaluation.models import Evaluation, Phase

    phase = Phase.objects.get(pk=phase_pk)

    with check_lock_acquired():
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


@lambda_task(queue=LambdaTaskQueueChoices.MEM8G)
def assign_evaluation_permissions(*, phase_pks: list[str | uuid.UUID]):
    from grandchallenge.evaluation.models import Evaluation

    evals = Evaluation.objects.filter(
        submission__phase__id__in=phase_pks,
    )

    for e in evals:
        e.assign_permissions()


@lambda_task(queue=LambdaTaskQueueChoices.MEM8G)
def assign_submission_permissions(*, phase_pk: str | uuid.UUID):
    from grandchallenge.evaluation.models import Submission

    for sub in Submission.objects.filter(phase__id=phase_pk):
        sub.assign_permissions()


@lambda_task
def cancel_external_evaluations_past_timeout():
    from grandchallenge.evaluation.models import Evaluation

    timeout_threshold = now() - timedelta(
        seconds=settings.EXTERNAL_EVALUATION_TIMEOUT_IN_SECONDS
    )

    for eval in Evaluation.objects.filter(
        status=Evaluation.CLAIMED,
        claimed_at__lt=timeout_threshold,
    ).iterator(chunk_size=1000):
        eval.update_status(
            status=Evaluation.CANCELLED,
            error_message="External evaluation timed out.",
            compute_cost_euro_millicents=0,
        )
