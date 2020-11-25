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
from grandchallenge.subdomains.utils import reverse


@shared_task
def create_algorithm_jobs_for_session(*_, upload_session_pk):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)

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

    if algorithm_image:
        for image in images:
            creator = None if session is None else session.creator
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
    failed_jobs = Job.objects.filter(
        status=Job.FAILURE, pk__in=job_pks
    ).distinct()

    if failed_jobs.exists():
        # Note: this would not work if you could route jobs to different
        # algorithms from 1 upload session, but that is not supported right now
        algorithm = failed_jobs.first().algorithm_image.algorithm
        creator = failed_jobs.first().creator

        experiment_url = reverse(
            "algorithms:jobs-list", kwargs={"slug": algorithm.slug}
        )
        if session_pk is not None:
            experiment_url = reverse(
                "algorithms:execution-session-detail",
                kwargs={"slug": algorithm.slug, "pk": session_pk},
            )

        message = (
            f"Unfortunately {failed_jobs.count()} of your jobs for algorithm "
            f"'{algorithm.title}' failed with an error. "
            f"You can inspect the output and error messages at "
            f"{experiment_url}.\n\n"
            f"You may wish to try and correct these errors and try again, "
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
