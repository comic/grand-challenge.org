from celery import chain, chord, group, shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.db.transaction import on_commit
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.exceptions import ImageImportError
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    DEFAULT_INPUT_INTERFACE_SLUG,
    Job,
)
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.cases.tasks import build_images
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.credits.models import Credit
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.subdomains.utils import reverse


@shared_task
def run_algorithm_job_for_inputs(*, job_pk, upload_pks):
    start_jobs = execute_algorithm_job_for_inputs.signature(
        kwargs={"job_pk": job_pk}, immutable=True
    )
    if upload_pks:
        image_tasks = group(
            chain(
                build_images.signature(
                    kwargs={"upload_session_pk": upload_pk}, immutable=True
                ),
                add_images_to_component_interface_value.signature(
                    kwargs={
                        "component_interface_value_pk": civ_pk,
                        "upload_session_pk": upload_pk,
                    },
                    immutable=True,
                ),
            )
            for civ_pk, upload_pk in upload_pks.items()
        )
        start_jobs = chord(image_tasks, start_jobs).on_error(
            group(on_job_creation_error.s(job_pk=job_pk))
        )

    on_commit(start_jobs.apply_async)


@shared_task(bind=True)
def on_job_creation_error(self, task_id, *args, **kwargs):
    job_pk = kwargs.pop("job_pk")
    job = Job.objects.get(pk=job_pk)

    # Send an email to the algorithm editors and creator on job failure
    linked_task = send_failed_job_notification.signature(
        kwargs={"job_pk": job.pk}, immutable=True
    )

    error_message = ""
    missing_inputs = list(civ for civ in job.inputs.all() if not civ.has_value)
    if missing_inputs:
        error_message += (
            f"Job can't be started, input is missing for "
            f"{oxford_comma([c.interface.title for c in missing_inputs])}"
        )

    res = self.AsyncResult(task_id).result

    if isinstance(res, ImageImportError):
        error_message += str(res)

    job.update_status(
        status=job.FAILURE, error_message=error_message,
    )

    on_commit(linked_task.apply_async)


@shared_task
def add_images_to_component_interface_value(
    *, component_interface_value_pk, upload_session_pk
):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)

    if session.image_set.count() != 1:
        error_message = "Image imports should result in a single image"
        session.status = RawImageUploadSession.FAILURE
        session.error_message = error_message
        session.save()
        raise ImageImportError(error_message)

    civ = ComponentInterfaceValue.objects.get(pk=component_interface_value_pk)
    civ.image = session.image_set.get()
    civ.full_clean()
    civ.save()

    civ.image.update_viewer_groups_permissions()


@shared_task
def execute_algorithm_job_for_inputs(*, job_pk):
    job = Job.objects.get(pk=job_pk)

    # Send an email to the algorithm editors and creator on job failure
    task_on_success = send_failed_job_notification.signature(
        kwargs={"job_pk": str(job.pk)}, immutable=True
    )

    # check if all ComponentInterfaceValue's have a value.
    # Todo: move this check to execute() code when using inputs is done
    missing_inputs = list(civ for civ in job.inputs.all() if not civ.has_value)
    if missing_inputs:
        job.update_status(
            status=job.FAILURE,
            error_message=(
                f"Job can't be started, input is missing for "
                f"{oxford_comma([c.interface.title for c in missing_inputs])}"
            ),
        )
        on_commit(task_on_success.apply_async)
    else:
        job.task_on_success = task_on_success
        job.save()
        on_commit(job.execute)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def create_algorithm_jobs_for_session(
    *, upload_session_pk, algorithm_image_pk
):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)
    algorithm_image = AlgorithmImage.objects.get(pk=algorithm_image_pk)

    # Editors group should be able to view session jobs for debugging
    algorithm_editors = [algorithm_image.algorithm.editors_group]

    # Send an email to the algorithm editors and creator on job failure
    task_on_success = send_failed_session_jobs_notifications.signature(
        kwargs={
            "session_pk": str(session.pk),
            "algorithm_pk": str(algorithm_image.algorithm.pk),
        },
        immutable=True,
    )

    default_input_interface = ComponentInterface.objects.get(
        slug=DEFAULT_INPUT_INTERFACE_SLUG
    )

    with transaction.atomic():
        civ_sets = [
            {
                ComponentInterfaceValue.objects.create(
                    interface=default_input_interface, image=image
                )
            }
            for image in session.image_set.all()
        ]

        new_jobs = create_algorithm_jobs(
            algorithm_image=algorithm_image,
            civ_sets=civ_sets,
            creator=session.creator,
            extra_viewer_groups=algorithm_editors,
            extra_logs_viewer_groups=algorithm_editors,
            task_on_success=task_on_success,
        )

        unscheduled_jobs = len(civ_sets) - len(new_jobs)

        if session.creator is not None and unscheduled_jobs:
            experiment_url = reverse(
                "algorithms:execution-session-detail",
                kwargs={
                    "slug": algorithm_image.algorithm.slug,
                    "pk": upload_session_pk,
                },
            )
            Notification.send(
                type=NotificationType.NotificationTypeChoices.JOB_STATUS,
                actor=session.creator,
                message=f"Unfortunately {unscheduled_jobs} of the jobs for algorithm "
                f"{algorithm_image.algorithm.title} were not started because "
                f"the number of allowed jobs was reached.",
                target=algorithm_image.algorithm,
                description=experiment_url,
            )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def create_algorithm_jobs_for_archive(
    *, archive_pks, archive_item_pks=None, algorithm_pks=None
):
    for archive in Archive.objects.filter(pk__in=archive_pks).all():
        # Only the archive groups should be able to view the job
        # Can be shared with the algorithm editor if needed
        archive_groups = [
            archive.editors_group,
            archive.uploaders_group,
            archive.users_group,
        ]

        if algorithm_pks is not None:
            algorithms = Algorithm.objects.filter(pk__in=algorithm_pks).all()
        else:
            algorithms = archive.algorithms.all()

        if archive_item_pks is not None:
            archive_items = archive.items.filter(pk__in=archive_item_pks)
        else:
            archive_items = archive.items.all()

        for algorithm in algorithms:
            create_algorithm_jobs(
                algorithm_image=algorithm.latest_ready_image,
                civ_sets=[
                    {*ai.values.all()}
                    for ai in archive_items.prefetch_related(
                        "values__interface"
                    )
                ],
                creator=None,
                extra_viewer_groups=archive_groups,
                # NOTE: no emails in case the logs leak data
                # to the algorithm editors
                task_on_success=None,
            )


def create_algorithm_jobs(
    *,
    algorithm_image,
    civ_sets,
    creator=None,
    extra_viewer_groups=None,
    extra_logs_viewer_groups=None,
    max_jobs=None,
    task_on_success=None,
    task_on_failure=None,
):
    """
    Creates algorithm jobs for sets of component interface values

    Parameters
    ----------
    algorithm_image
        The algorithm image to use
    civ_sets
        The sets of component interface values that will be used as input
        for the algorithm image
    creator
        The creator of the algorithm jobs
    extra_viewer_groups
        The groups that will also get permission to view the jobs
    extra_logs_viewer_groups
        The groups that will also get permission to view the logs for
        the jobs
    max_jobs
        The maximum number of jobs to schedule
    task_on_success
        Celery task that is run on job success. This must be able
        to handle being called more than once, and in parallel.
    task_on_failure
        Celery task that is run on job failure
    """
    civ_sets = filter_civs_for_algorithm(
        civ_sets=civ_sets, algorithm_image=algorithm_image
    )

    if (
        creator
        and not algorithm_image.algorithm.is_editor(creator)
        and algorithm_image.algorithm.credits_per_job > 0
    ):
        n_jobs = remaining_jobs(
            creator=creator, algorithm_image=algorithm_image
        )
        if n_jobs > 0:
            civ_sets = civ_sets[:n_jobs]
        else:
            # Out of credits
            return []

    if max_jobs is not None:
        civ_sets = civ_sets[:max_jobs]

    jobs = []
    for civ_set in civ_sets:
        with transaction.atomic():
            j = Job.objects.create(
                creator=creator,
                algorithm_image=algorithm_image,
                task_on_success=task_on_success,
                task_on_failure=task_on_failure,
            )
            j.inputs.set(civ_set)

            if extra_viewer_groups is not None:
                j.viewer_groups.add(*extra_viewer_groups)

            if extra_logs_viewer_groups is not None:
                for g in extra_logs_viewer_groups:
                    assign_perm("algorithms.view_logs", g, j)

            jobs.append(j)

            on_commit(j.execute)

    return jobs


def filter_civs_for_algorithm(*, civ_sets, algorithm_image):
    """
    Removes sets of civs that are invalid for new jobs

    Parameters
    ----------
    civ_sets
        Iterable of sets of ComponentInterfaceValues that are candidate for
        new Jobs
    algorithm_image
        The algorithm image to use for new job

    Returns
    -------
    Filtered set of ComponentInterfaceValues
    """
    input_interfaces = {*algorithm_image.algorithm.inputs.all()}

    existing_jobs = {
        frozenset(j.inputs.all())
        for j in Job.objects.filter(algorithm_image=algorithm_image)
        .annotate(
            inputs_match_count=Count(
                "inputs",
                filter=Q(
                    inputs__in={civ for civ_set in civ_sets for civ in civ_set}
                ),
            )
        )
        .filter(inputs_match_count=len(input_interfaces))
        .prefetch_related("inputs")
    }

    valid_job_inputs = []

    for civ_set in civ_sets:
        # Check interfaces are complete
        civ_interfaces = {civ.interface for civ in civ_set}
        if input_interfaces.issubset(civ_interfaces):
            # If the algorithm works with a subset of the interfaces
            # present in the set then only feed these through to the algorithm
            valid_input = {
                civ for civ in civ_set if civ.interface in input_interfaces
            }
        else:
            continue

        # Check job has not been run
        if frozenset(valid_input) in existing_jobs:
            continue

        valid_job_inputs.append(valid_input)

    return valid_job_inputs


def remaining_jobs(*, creator, algorithm_image):
    user_credit = Credit.objects.get(user=creator)
    jobs = Job.credits_set.spent_credits(user=creator)
    if jobs["total"]:
        total_jobs = user_credit.credits - jobs["total"]
    else:
        total_jobs = user_credit.credits
    return int(total_jobs / max(algorithm_image.algorithm.credits_per_job, 1))


@shared_task
def send_failed_job_notification(*, job_pk):
    job = Job.objects.get(pk=job_pk)

    if job.status == Job.FAILURE and job.creator is not None:
        algorithm = job.algorithm_image.algorithm
        experiment_url = reverse(
            "algorithms:job-list", kwargs={"slug": algorithm.slug}
        )
        Notification.send(
            type=NotificationType.NotificationTypeChoices.JOB_STATUS,
            actor=job.creator,
            message=f"Unfortunately one of the jobs for algorithm {algorithm.title} "
            f"failed with an error",
            target=algorithm,
            description=experiment_url,
        )


@shared_task
def send_failed_session_jobs_notifications(*, session_pk, algorithm_pk):
    session = RawImageUploadSession.objects.get(pk=session_pk)
    algorithm = Algorithm.objects.get(pk=algorithm_pk)

    queryset = Job.objects.filter(
        inputs__image__in=session.image_set.all()
    ).distinct()

    pending_jobs = queryset.exclude(
        status__in=[Job.SUCCESS, Job.FAILURE, Job.CANCELLED]
    )
    failed_jobs = queryset.filter(status=Job.FAILURE)

    if pending_jobs.exists():
        # Nothing to do
        return
    elif session.creator is not None:
        # TODO this task isn't really idempotent
        # This task is not guaranteed to only be delivered once after
        # all jobs have completed. We could end up in a situation where
        # this is run multiple times after the action is sent and
        # multiple notifications sent with the same message.
        # We cannot really check if the action has already been sent
        # which would then reduce this down to a race condition, but
        # still a problem.
        # We could of course just notify on each failure, but then
        # this should be an on_error task for each job.
        failed_jobs_count = failed_jobs.count()
        if failed_jobs_count:
            experiment_url = reverse(
                "algorithms:execution-session-detail",
                kwargs={"slug": algorithm.slug, "pk": session_pk},
            )
            Notification.send(
                type=NotificationType.NotificationTypeChoices.JOB_STATUS,
                actor=session.creator,
                message=f"Unfortunately {failed_jobs_count} of the jobs for "
                f"algorithm {algorithm.title} failed with an error ",
                target=algorithm,
                description=experiment_url,
            )
