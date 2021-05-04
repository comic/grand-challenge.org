from celery import chord, group, shared_task
from django.apps import apps
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db.transaction import on_commit

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
from grandchallenge.credits.models import Credit
from grandchallenge.evaluation.tasks import set_evaluation_inputs
from grandchallenge.subdomains.utils import reverse


@shared_task
def run_algorithm_job_for_inputs(*, job_pk, upload_pks):
    start_jobs = execute_algorithm_job_for_inputs.signature(
        kwargs={"job_pk": job_pk}, immutable=True
    )
    if upload_pks:
        image_tasks = group(
            add_images_to_component_interface_value.signature(
                kwargs={
                    "component_interface_value_pk": civ_pk,
                    "upload_pk": upload_pk,
                },
                immutable=True,
            )
            for civ_pk, upload_pk in upload_pks.items()
        )
        start_jobs = chord(image_tasks, start_jobs).on_error(
            group(on_chord_error.s(job_pk=job_pk))
        )

    on_commit(start_jobs.apply_async)


@shared_task(bind=True)
def on_chord_error(self, task_id, *args, **kwargs):
    job_pk = kwargs.pop("job_pk")
    job = Job.objects.get(pk=job_pk)

    # Send an email to the algorithm editors and creator on job failure
    linked_task = send_failed_jobs_email.signature(
        kwargs={"job_pks": [job.pk]}, immutable=True
    )

    error_message = ""
    missing_inputs = list(civ for civ in job.inputs.all() if not civ.has_value)
    if missing_inputs:
        error_message += (
            f"Job can't be started, input is missing for interface(s):"
            f" {list(c.interface.title for c in missing_inputs)} "
        )
    res = self.AsyncResult(task_id).result
    if isinstance(res, Exception):
        error_message += str(res)
    job.update_status(
        status=job.FAILURE, error_message=error_message,
    )

    on_commit(linked_task.apply_async)


@shared_task
def add_images_to_component_interface_value(
    *, component_interface_value_pk, upload_pk
):
    session = RawImageUploadSession.objects.get(pk=upload_pk)
    session.status = RawImageUploadSession.REQUEUED
    session.save()

    build_images(upload_session_pk=upload_pk)

    if session.image_set.count() != 1:
        error_message = "Image imports should result in a single image"
        session.status = RawImageUploadSession.FAILURE
        session.error_message = error_message
        session.save()
        raise ValueError(error_message)

    civ = ComponentInterfaceValue.objects.get(pk=component_interface_value_pk)
    civ.image = session.image_set.get()
    civ.save()

    civ.image.update_viewer_groups_permissions()


@shared_task
def execute_algorithm_job_for_inputs(*, job_pk):
    job = Job.objects.get(pk=job_pk)

    # Send an email to the algorithm editors and creator on job failure
    linked_task = send_failed_jobs_email.signature(
        kwargs={"job_pks": [job.pk]}, immutable=True
    )

    # check if all ComponentInterfaceValue's have a value.
    # Todo: move this check to execute() code when using inputs is done
    missing_inputs = list(civ for civ in job.inputs.all() if not civ.has_value)
    if missing_inputs:
        job.update_status(
            status=job.FAILURE,
            error_message=(
                f"Job can't be started, input is missing for interface(s):"
                f" {list(c.interface.title for c in missing_inputs)}"
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
    linked_task = send_failed_jobs_email.signature(
        kwargs={"session_pk": session.pk}, immutable=True
    )

    execute_jobs(
        algorithm_image=algorithm_image,
        images=session.image_set.all(),
        creator=session.creator,
        extra_viewer_groups=groups,
        linked_task=linked_task,
    )


@shared_task
def create_algorithm_jobs_for_archive(
    *, archive_pks, civ_pks=None, algorithm_pks=None
):
    # Send an email to the algorithm editors on job failure
    linked_task = send_failed_jobs_email.signature(kwargs={}, immutable=True)

    for archive in Archive.objects.filter(pk__in=archive_pks).all():
        archive_groups = [
            archive.editors_group,
            archive.uploaders_group,
            archive.users_group,
        ]

        if algorithm_pks is not None:
            algorithms = Algorithm.objects.filter(pk__in=algorithm_pks).all()
        else:
            algorithms = archive.algorithms.all()

        # TODO: when other types of civ can be added to algotihms this would
        # need to be grouped by ArchiveItem
        if civ_pks is not None:
            civs = ComponentInterfaceValue.objects.filter(pk__in=civ_pks).all()
        else:
            civs = archive.items.values_list("values", flat=True)

        for algorithm in algorithms:
            # Editors group should be able to view archive jobs for debugging
            groups = [*archive_groups, algorithm.editors_group]

            execute_jobs(
                algorithm_image=algorithm.latest_ready_image,
                civs=civs,
                creator=None,
                extra_viewer_groups=groups,
                linked_task=linked_task,
            )


@shared_task
def create_algorithm_jobs_for_evaluation(*, evaluation_pk):
    Evaluation = apps.get_model(  # noqa: N806
        app_label="evaluation", model_name="Evaluation"
    )
    evaluation = Evaluation.objects.get(pk=evaluation_pk)

    # Only the challenge admins should be able to view these jobs, never
    # the algorithm editors as these are participants - they must never
    # be able to see the test data.
    groups = [evaluation.submission.phase.challenge.admins_group]

    # Once the algorithm has been run, score the submission. No emails as
    # algorithm editors should not have access to the underlying images.
    linked_task = set_evaluation_inputs.signature(
        kwargs={"evaluation_pk": evaluation.pk}, immutable=True
    )

    execute_jobs(
        algorithm_image=evaluation.submission.algorithm_image,
        images=evaluation.submission.phase.archive.items.values_list(
            "values", flat=True
        ),
        creator=None,
        extra_viewer_groups=groups,
        linked_task=linked_task,
    )


def execute_jobs(
    *,
    algorithm_image,
    images=None,
    civs=None,
    creator=None,
    extra_viewer_groups=None,
    linked_task=None,
):
    jobs = create_algorithm_jobs(
        algorithm_image=algorithm_image,
        images=images,
        civs=civs,
        creator=creator,
        extra_viewer_groups=extra_viewer_groups,
    )

    if jobs:
        workflow = group(j.signature for j in jobs)

        if linked_task is not None:
            linked_task.kwargs.update({"job_pks": [j.pk for j in jobs]})
            workflow |= linked_task

        on_commit(workflow.apply_async)


def create_algorithm_job_with_inputs(
    *, algorithm_image, inputs, creator=None, extra_viewer_groups=None
):
    if not algorithm_image:
        return None

    if creator:
        if (
            not algorithm_image.algorithm.is_editor(creator)
            and algorithm_image.algorithm.credits_per_job > 0
        ):
            r = remaining_jobs(
                creator=creator, algorithm_image=algorithm_image
            )
            if r <= 0:
                # no more credits to start job, should not happen as
                # this is handled in the UI already
                return None

    job = Job.objects.create(creator=creator, algorithm_image=algorithm_image)
    job.inputs.set(
        [ComponentInterfaceValue.objects.get(pk=pk) for pk in inputs]
    )

    if extra_viewer_groups is not None:
        job.viewer_groups.add(*extra_viewer_groups)

    return job


def create_algorithm_jobs(  # noqa: C901
    *,
    algorithm_image,
    images=None,
    civs=None,
    creator=None,
    extra_viewer_groups=None,
):
    default_input_interface = ComponentInterface.objects.get(
        slug=DEFAULT_INPUT_INTERFACE_SLUG
    )

    jobs = []
    if not images:
        images = []
    if not civs:
        civs = []

    if not algorithm_image:
        return jobs

    if creator:
        if (
            not algorithm_image.algorithm.is_editor(creator)
            and algorithm_image.algorithm.credits_per_job > 0
        ):
            images = images[
                : remaining_jobs(
                    creator=creator, algorithm_image=algorithm_image
                )
            ]
            civs = civs[
                : remaining_jobs(
                    creator=creator, algorithm_image=algorithm_image
                )
            ]

    for civ in civs:
        j = Job.objects.create(
            creator=creator, algorithm_image=algorithm_image
        )
        j.inputs.set([civ])

        if extra_viewer_groups is not None:
            j.viewer_groups.add(*extra_viewer_groups)
        jobs.append(j)

    for image in images:
        if not ComponentInterfaceValue.objects.filter(
            interface=default_input_interface,
            image=image,
            algorithms_jobs_as_input__algorithm_image=algorithm_image,
            algorithms_jobs_as_input__creator=creator,
        ).exists():
            j = Job.objects.create(
                creator=creator, algorithm_image=algorithm_image
            )
            j.inputs.set(
                [
                    ComponentInterfaceValue.objects.create(
                        interface=default_input_interface, image=image
                    )
                ]
            )

            if extra_viewer_groups is not None:
                j.viewer_groups.add(*extra_viewer_groups)

            jobs.append(j)

    return jobs


def remaining_jobs(*, creator, algorithm_image):
    user_credit = Credit.objects.get(user=creator)
    jobs = Job.credits_set.spent_credits(user=creator)
    if jobs["total"]:
        total_jobs = user_credit.credits - jobs["total"]
    else:
        total_jobs = user_credit.credits
    return int(total_jobs / max(algorithm_image.algorithm.credits_per_job, 1))


@shared_task
def send_failed_jobs_email(*, job_pks, session_pk=None):
    excluded_images_count = 0

    if session_pk:
        session = RawImageUploadSession.objects.get(pk=session_pk)
        excluded_images_count = session.image_set.filter(
            componentinterfacevalue__algorithms_jobs_as_input__isnull=True
        ).count()

    failed_jobs = Job.objects.filter(
        status=Job.FAILURE, pk__in=job_pks
    ).distinct()

    if failed_jobs.exists() or excluded_images_count > 0:
        # Note: this would not work if you could route jobs to different
        # algorithms from 1 upload session, but that is not supported right now
        algorithm = failed_jobs.first().algorithm_image.algorithm
        creator = failed_jobs.first().creator

        experiment_url = reverse(
            "algorithms:job-list", kwargs={"slug": algorithm.slug}
        )
        if session_pk is not None:
            experiment_url = reverse(
                "algorithms:execution-session-detail",
                kwargs={"slug": algorithm.slug, "pk": session_pk},
            )

        message = ""
        if failed_jobs.count() > 0:
            message = (
                f"Unfortunately {failed_jobs.count()} of your jobs for algorithm "
                f"'{algorithm.title}' failed with an error. "
            )

        if excluded_images_count > 0:
            message = (
                f"{message}"
                f"{excluded_images_count} of your jobs for algorithm "
                f"'{algorithm.title}' were not started because the number of allowed "
                f"jobs was reached. "
            )

        message = (
            f"{message}"
            f"You can inspect the output and any error messages at "
            f"{experiment_url}.\n\n"
            f"You may wish to try and correct any errors and try again, "
            f"or contact the algorithm editors. "
            f"The following information may help them:\n"
        )
        if creator is not None:
            message += f"User: {creator.username}\n"
        if session_pk is not None:
            message += f"Experiment ID: {session_pk}\n"

        receivers = {o.email for o in algorithm.editors_group.user_set.all()}
        if creator is not None:
            receivers.add(creator.email)

        for email in receivers:
            send_mail(
                subject=(
                    f"[{Site.objects.get_current().domain.lower()}] "
                    f"[{algorithm.title.lower()}] "
                    f"Jobs Failed"
                ),
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
