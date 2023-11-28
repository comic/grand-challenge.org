import logging
import uuid
from statistics import mean, median

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.db.transaction import on_commit
from redis.exceptions import LockError

from grandchallenge.algorithms.exceptions import TooManyJobsScheduled
from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.tasks import create_algorithm_jobs
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.tasks import _retry
from grandchallenge.core.cache import _cache_key_from_method
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.evaluation.utils import Metric, rank_results
from grandchallenge.notifications.models import Notification, NotificationType

logger = logging.getLogger(__name__)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
@transaction.atomic
def create_evaluation(*, submission_pk, max_initial_jobs=1):
    """Creates an Evaluation for a Submission.

    Parameters
    ----------
    submission_pk
        The primary key of the Submission
    max_initial_jobs
        The maximum number of algorithm jobs to schedule first

    """
    Submission = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Submission"
    )
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )

    submission = Submission.objects.get(pk=submission_pk)

    if not submission.predictions_file and submission.user_upload:
        submission.user_upload.copy_object(
            to_field=submission.predictions_file
        )
        submission.user_upload.delete()

    # TODO - move this to the forms and make it an input here
    method = submission.phase.active_image
    if not method:
        logger.info("No method ready for this submission")
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.MISSING_METHOD,
            message="missing method",
            actor=submission.creator,
            action_object=submission,
            target=submission.phase,
        )
        return

    evaluation, created = Evaluation.objects.get_or_create(
        submission=submission, method=method
    )
    if not created:
        logger.info("Evaluation already created for this submission")
        return

    if submission.algorithm_image:
        on_commit(
            lambda: create_algorithm_jobs_for_evaluation.apply_async(
                kwargs={
                    "evaluation_pk": evaluation.pk,
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

        evaluation.inputs.set([civ])
        on_commit(evaluation.execute)
    else:
        raise RuntimeError("No algorithm or predictions file found")


@shared_task(
    **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"],
    throws=(
        TooManyJobsScheduled,
        LockError,
    ),
)
def create_algorithm_jobs_for_evaluation(
    *, evaluation_pk, max_jobs=1, retries=0
):
    """Creates the algorithm jobs for the evaluation.

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

    def retry_with_delay():
        _retry(
            task=create_algorithm_jobs_for_evaluation,
            signature_kwargs={
                "kwargs": {
                    "evaluation_pk": evaluation_pk,
                    "max_jobs": max_jobs,
                },
                "immutable": True,
            },
            retries=retries,
        )

    if Job.objects.active().count() >= settings.ALGORITHMS_MAX_ACTIVE_JOBS:
        logger.info("Retrying task as too many jobs scheduled")
        retry_with_delay()
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
    # be able to see the test data.
    challenge_admins = [evaluation.submission.phase.challenge.admins_group]

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

    try:
        # Method is expensive so only allow one process at a time
        with cache.lock(
            _cache_key_from_method(create_algorithm_jobs),
            timeout=settings.CELERY_TASK_TIME_LIMIT,
            blocking_timeout=10,
        ):
            jobs = create_algorithm_jobs(
                algorithm_image=evaluation.submission.algorithm_image,
                civ_sets=[
                    {*ai.values.all()}
                    for ai in evaluation.submission.phase.archive.items.prefetch_related(
                        "values__interface"
                    )
                ],
                extra_viewer_groups=challenge_admins,
                extra_logs_viewer_groups=challenge_admins,
                task_on_success=task_on_success,
                task_on_failure=task_on_failure,
                max_jobs=max_jobs,
                time_limit=evaluation.submission.phase.algorithm_time_limit,
            )
    except (TooManyJobsScheduled, LockError) as error:
        logger.info(f"Retrying task due to: {error}")
        retry_with_delay()
        raise

    if not jobs:
        # No more jobs created from this task, so everything must be
        # ready for evaluation, handles archives with only one item
        # and re-evaluation of existing submissions with new methods
        set_evaluation_inputs.signature(
            kwargs={"evaluation_pk": str(evaluation.pk)},
            immutable=True,
        ).apply_async()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
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
    ).update(status=Job.CANCELLED)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def set_evaluation_inputs(*, evaluation_pk):
    """Sets the inputs to the Evaluation for an algorithm submission.

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

    has_pending_jobs = (
        Job.objects.active()
        .filter(
            algorithm_image__submission__evaluation=evaluation_pk,
            creator__isnull=True,  # Evaluation inference jobs have no creator
        )
        .exists()
    )

    if has_pending_jobs:
        logger.info("Nothing to do: the algorithm has pending jobs.")
        return

    evaluation_queryset = Evaluation.objects.filter(
        pk=evaluation_pk
    ).select_for_update()

    with transaction.atomic():
        # Acquire lock
        evaluation = evaluation_queryset.get()

        if evaluation.status != evaluation.EXECUTING_PREREQUISITES:
            logger.info(
                f"Nothing to do: evaluation is {evaluation.get_status_display()}."
            )
            return

        algorithm_inputs = {
            *evaluation.submission.phase.algorithm_inputs.all()
        }

        civ_sets = {
            i.values.all()
            for i in evaluation.submission.phase.archive.items.annotate(
                interface_match_count=Count(
                    "values", filter=Q(values__interface__in=algorithm_inputs)
                )
            )
            .filter(interface_match_count=len(algorithm_inputs))
            .prefetch_related("values")
        }

        successful_jobs = (
            Job.objects.filter(
                algorithm_image=evaluation.submission.algorithm_image,
                status=Job.SUCCESS,
            )
            .annotate(
                inputs_match_count=Count(
                    "inputs",
                    filter=Q(
                        inputs__in={
                            civ for civ_set in civ_sets for civ in civ_set
                        }
                    ),
                )
            )
            .filter(
                inputs_match_count=evaluation.submission.phase.algorithm_inputs.count()
            )
            .distinct()
            .prefetch_related("outputs__interface", "inputs__interface")
            .select_related("algorithm_image__algorithm")
        )

        if successful_jobs.count() == len(civ_sets):
            from grandchallenge.algorithms.serializers import JobSerializer
            from grandchallenge.components.models import (
                ComponentInterface,
                ComponentInterfaceValue,
            )

            serializer = JobSerializer(successful_jobs.all(), many=True)
            interface = ComponentInterface.objects.get(
                slug="predictions-json-file"
            )
            civ = ComponentInterfaceValue.objects.create(
                interface=interface, value=serializer.data
            )

            output_to_job = {
                o: j for j in successful_jobs.all() for o in j.outputs.all()
            }

            evaluation.inputs.set([civ, *output_to_job.keys()])
            evaluation.input_prefixes = {
                str(o.pk): f"{j.pk}/output/" for o, j in output_to_job.items()
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
@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
@transaction.atomic
def calculate_ranks(*, phase_pk: uuid.UUID):
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
            Metric(path=col["path"], reverse=col["order"] == phase.DESCENDING)
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
            submission__phase=phase, published=True, status=Evaluation.SUCCESS
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

    for leaderboard in phase.combinedleaderboard_set.all():
        leaderboard.schedule_combined_ranks_update()


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


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
@transaction.atomic
def update_combined_leaderboard(*, pk):
    CombinedLeaderboard = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="CombinedLeaderboard"
    )

    leaderboard = CombinedLeaderboard.objects.get(pk=pk)
    leaderboard.update_combined_ranks_cache()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
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


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
@transaction.atomic
def assign_submission_permissions(*, phase_pk: uuid.UUID):
    Submission = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Submission"
    )
    for sub in Submission.objects.filter(phase__id=phase_pk):
        sub.assign_permissions()
