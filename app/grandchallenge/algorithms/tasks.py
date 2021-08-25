from actstream import action
from celery import chain, chord, group, shared_task
from django.db.models import Count, Q
from django.db.transaction import on_commit

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
    linked_task = send_failed_job_notification.signature(
        kwargs={"job_pk": job.pk}, immutable=True
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
        on_commit(linked_task.apply_async)
    else:
        workflow = job.signature | linked_task
        on_commit(workflow.apply_async)


@shared_task
def create_algorithm_jobs_for_session(
    *, upload_session_pk, algorithm_image_pk
):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)
    algorithm_image = AlgorithmImage.objects.get(pk=algorithm_image_pk)

    # Editors group should be able to view session jobs for debugging
    groups = [algorithm_image.algorithm.editors_group]

    # Send an email to the algorithm editors and creator on job failure
    linked_task = send_failed_session_jobs_notifications.signature(
        kwargs={
            "session_pk": session.pk,
            "algorithm_pk": algorithm_image.algorithm.pk,
        },
        immutable=True,
    )

    default_input_interface = ComponentInterface.objects.get(
        slug=DEFAULT_INPUT_INTERFACE_SLUG
    )
    civ_sets = [
        {
            ComponentInterfaceValue.objects.create(
                interface=default_input_interface, image=image
            )
        }
        for image in session.image_set.all()
    ]

    execute_jobs(
        algorithm_image=algorithm_image,
        civ_sets=civ_sets,
        creator=session.creator,
        extra_viewer_groups=groups,
        linked_task=linked_task,
    )


@shared_task
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
            execute_jobs(
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
                linked_task=None,
            )


def execute_jobs(
    *,
    algorithm_image,
    civ_sets,
    creator=None,
    extra_viewer_groups=None,
    linked_task=None,
    on_error=None,
    execute_one_first=False,  # TODO fixme
):
    """
    Execute an algorithm image on sets of component interface values.

    The resulting jobs will be applied in parallel. Note that using
    a chord here is not supported due to the message size limit of
    SQS (https://github.com/celery/kombu/issues/279).

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
        The viewer groups that will also get access to view the job
    linked_task
        A task that is run after each job completion. This must be able
        to handle being called more than once, and in parallel.
    on_error
        A task that is run every time a job fails
    execute_one_first
        Option to run only one task first
    """
    jobs = create_algorithm_jobs(
        algorithm_image=algorithm_image,
        civ_sets=civ_sets,
        creator=creator,
        extra_viewer_groups=extra_viewer_groups,
    )

    for j in jobs:
        workflow = j.signature

        if linked_task is not None:
            workflow |= linked_task

        if on_error is not None:
            workflow = workflow.on_error(on_error)

        on_commit(workflow.apply_async)


def create_algorithm_jobs(
    *, algorithm_image, civ_sets, creator=None, extra_viewer_groups=None,
):
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

    jobs = []
    for civ_set in civ_sets:
        j = Job.objects.create(
            creator=creator, algorithm_image=algorithm_image
        )
        j.inputs.set(civ_set)

        if extra_viewer_groups is not None:
            j.viewer_groups.add(*extra_viewer_groups)

        jobs.append(j)

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
        action.send(
            sender=algorithm,
            verb=(
                f"Unfortunately one of the jobs for algorithm {algorithm.title} "
                f"failed with an error."
            ),
            description=f"{experiment_url}",
            target=job.creator,
        )


@shared_task
def send_failed_session_jobs_notifications(*, session_pk, algorithm_pk):
    session = RawImageUploadSession.objects.get(pk=session_pk)
    algorithm = Algorithm.objects.get(pk=algorithm_pk)

    if session.creator is not None:
        experiment_url = reverse(
            "algorithms:execution-session-detail",
            kwargs={"slug": algorithm.slug, "pk": session_pk},
        )

        excluded_images_count = session.image_set.filter(
            componentinterfacevalue__algorithms_jobs_as_input__isnull=True
        ).count()

        if excluded_images_count > 0:
            action.send(
                sender=algorithm,
                verb=(
                    f"Unfortunately {excluded_images_count} of the jobs "
                    f"for algorithm {algorithm.title} were not started because the number of allowed "
                    f"jobs was reached."
                ),
                description=f"{experiment_url}",
                target=session.creator,
            )

        failed_jobs = Job.objects.filter(
            status=Job.FAILURE, inputs__image__in=session.image_set.all()
        ).distinct()

        if failed_jobs.exists():
            action.send(
                sender=algorithm,
                verb=(
                    f"Unfortunately {failed_jobs.count()} of the jobs for algorithm {algorithm.title} "
                    f"failed with an error."
                ),
                description=f"{experiment_url}",
                target=session.creator,
            )
