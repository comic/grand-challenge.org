import logging
import uuid
from statistics import mean, median

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.db.models import Count, Q
from django.db.transaction import on_commit

from grandchallenge.algorithms.tasks import create_algorithm_jobs
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.evaluation.utils import Metric, rank_results
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.notifications.models import Notification, NotificationType

logger = logging.getLogger(__name__)


@shared_task
def create_evaluation(*, submission_pk, max_initial_jobs=1):
    """
    Creates an Evaluation for a Submission

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

    if (
        not submission.predictions_file
        and submission.staged_predictions_file_uuid
    ):
        uploaded_file = StagedAjaxFile(submission.staged_predictions_file_uuid)
        with uploaded_file.open() as f:
            submission.predictions_file.save(uploaded_file.name, File(f))

    # TODO - move this to the form and make it an input here
    method = submission.latest_ready_method
    if not method:
        logger.info("No method ready for this submission")
        Notification.send(
            type=NotificationType.NotificationTypeChoices.MISSING_METHOD,
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
        elif mimetype in ["text/plain", "application/csv"]:
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
        civ.full_clean()
        civ.save()

        evaluation.inputs.set([civ])
        on_commit(evaluation.execute)
    else:
        raise RuntimeError("No algorithm or predictions file found")


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
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
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evaluation = Evaluation.objects.get(pk=evaluation_pk)

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

    create_algorithm_jobs(
        algorithm_image=evaluation.submission.algorithm_image,
        civ_sets=[
            {*ai.values.all()}
            for ai in evaluation.submission.phase.archive.items.prefetch_related(
                "values__interface"
            )
        ],
        creator=None,
        extra_viewer_groups=challenge_admins,
        extra_logs_viewer_groups=challenge_admins,
        task_on_success=task_on_success,
        task_on_failure=task_on_failure,
        max_jobs=max_jobs,
    )

    evaluation.update_status(status=Evaluation.EXECUTING_PREREQUISITES)


@shared_task
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


@shared_task
def set_evaluation_inputs(*, evaluation_pk):
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
    Job = apps.get_model(  # noqa: N806
        app_label="algorithms", model_name="Job"
    )
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evaluation_queryset = Evaluation.objects.filter(
        pk=evaluation_pk
    ).select_for_update()

    with transaction.atomic():
        # Acquire lock
        evaluation = evaluation_queryset.get()

        civ_sets = {
            i.values.all()
            for i in evaluation.submission.phase.archive.items.all()
        }

        jobs_queryset = (
            Job.objects.filter(
                algorithm_image=evaluation.submission.algorithm_image,
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

        pending_jobs = jobs_queryset.exclude(
            status__in=[Job.SUCCESS, Job.FAILURE, Job.CANCELLED]
        )
        successful_jobs = jobs_queryset.filter(status=Job.SUCCESS)

        if (
            pending_jobs.exists()
            or evaluation.status != evaluation.EXECUTING_PREREQUISITES
        ):
            # Nothing to do
            return
        elif successful_jobs.count() == len(civ_sets):
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
        else:
            handle_failed_jobs(evaluation_pk=evaluation_pk)


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
