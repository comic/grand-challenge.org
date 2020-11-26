from celery import group, shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from grandchallenge.algorithms.models import (
    Algorithm,
    DEFAULT_INPUT_INTERFACE_SLUG,
    Job,
)
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.credits.models import Credit
from grandchallenge.subdomains.utils import reverse


@shared_task
def create_algorithm_jobs_for_session(*_, upload_session_pk):
    session = RawImageUploadSession.objects.select_related(
        "algorithm_image__algorithm"
    ).get(pk=upload_session_pk)

    create_algorithm_jobs(
        algorithm_image=session.algorithm_image,
        images=session.image_set.all(),
        session=session,
    )


@shared_task
def create_algorithm_jobs_for_archive_images(archive_pks, image_pks):
    for archive in Archive.objects.filter(pk__in=archive_pks).all():
        groups = [
            archive.editors_group,
            archive.uploaders_group,
            archive.users_group,
        ]
        for algorithm in archive.algorithms.all():
            create_algorithm_jobs(
                algorithm_image=algorithm.latest_ready_image,
                images=Image.objects.filter(pk__in=image_pks).all(),
                extra_viewer_groups=groups,
            )


@shared_task
def create_algorithm_jobs_for_archive_algorithms(archive_pks, algorithm_pks):
    for algorithm in Algorithm.objects.filter(pk__in=algorithm_pks).all():
        for archive in Archive.objects.filter(pk__in=archive_pks).all():
            groups = [
                archive.editors_group,
                archive.uploaders_group,
                archive.users_group,
            ]
            create_algorithm_jobs(
                algorithm_image=algorithm.latest_ready_image,
                images=archive.images.all(),
                extra_viewer_groups=groups,
            )


def create_algorithm_jobs(
    algorithm_image, images, session=None, extra_viewer_groups=None
):
    default_input_interface = ComponentInterface.objects.get(
        slug=DEFAULT_INPUT_INTERFACE_SLUG
    )

    jobs = []

    def remaining_jobs() -> int:
        user_credit = Credit.objects.get(user=session.creator)
        jobs = Job.credits_set.spent_credits(user=session.creator)

        if jobs["total"]:
            total_jobs = user_credit.credits - jobs["total"]
        else:
            total_jobs = user_credit.credits

        return int(
            total_jobs / max(algorithm_image.algorithm.credits_per_job, 1)
        )

    if algorithm_image:
        creator = None if session is None else session.creator
        if creator:
            if (
                not session.algorithm_image.algorithm.is_editor(creator)
                and session.algorithm_image.algorithm.credits_per_job > 0
            ):
                images = images[: remaining_jobs()]
        for image in images:
            if not ComponentInterfaceValue.objects.filter(
                interface=default_input_interface,
                image=image,
                algorithms_jobs_as_input__algorithm_image=algorithm_image,
                algorithms_jobs_as_input__creator=creator,
            ).exists():
                j = Job.objects.create(
                    creator=creator, algorithm_image=algorithm_image,
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


def create_jobs_workflow(jobs, session=None):
    job_signatures = [j.signature for j in jobs]
    job_pks = [j.pk for j in jobs]
    workflow = group(*job_signatures) | send_failed_jobs_email.signature(
        kwargs={
            "job_pks": job_pks,
            "session_pk": None if session is None else session.pk,
        }
    )
    return workflow


def execute_jobs(
    algorithm_image, images, session=None, extra_viewer_groups=None
):
    jobs = create_algorithm_jobs(
        algorithm_image,
        images,
        session=session,
        extra_viewer_groups=extra_viewer_groups,
    )
    if len(jobs) > 0:
        workflow = create_jobs_workflow(jobs, session=session)
        workflow.apply_async()


@shared_task
def send_failed_jobs_email(*_, job_pks, session_pk=None):
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
