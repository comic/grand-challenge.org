from celery import group, shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from grandchallenge.algorithms.models import DEFAULT_INPUT_INTERFACE_SLUG, Job
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.credits.models import Credit
from grandchallenge.subdomains.utils import reverse


@shared_task
def create_algorithm_jobs(*_, upload_session_pk):
    session = RawImageUploadSession.objects.select_related(
        "algorithm_image__algorithm"
    ).get(pk=upload_session_pk)

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
            total_jobs
            / max(session.algorithm_image.algorithm.credits_per_job, 1)
        )

    if session.creator and session.algorithm_image:
        session_images = session.image_set.all()
        if (
            not session.algorithm_image.algorithm.is_editor(session.creator)
            and session.algorithm_image.algorithm.credits_per_job > 0
        ):
            session_images = session_images[: remaining_jobs()]

        for image in session_images:
            if not ComponentInterfaceValue.objects.filter(
                interface=default_input_interface,
                image=image,
                algorithms_jobs_as_input__algorithm_image=session.algorithm_image,
                algorithms_jobs_as_input__creator=session.creator,
            ).exists():
                j = Job.objects.create(
                    creator=session.creator,
                    algorithm_image=session.algorithm_image,
                )
                j.inputs.set(
                    [
                        ComponentInterfaceValue.objects.create(
                            interface=default_input_interface, image=image
                        )
                    ]
                )
                jobs.append(j.signature)

    if jobs:
        workflow = group(*jobs) | send_failed_jobs_email.signature(
            kwargs={"upload_session_pk": upload_session_pk}
        )
        workflow.apply_async()


@shared_task
def send_failed_jobs_email(*_, upload_session_pk):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)

    excluded_images_count = session.image_set.filter(
        componentinterfacevalue__algorithms_jobs_as_input__isnull=True
    ).count()

    failed_jobs = Job.objects.filter(
        inputs__image__origin_id=upload_session_pk, status=Job.FAILURE
    ).distinct()

    if failed_jobs.exists() or excluded_images_count > 0:
        # Note: this would not work if you could route jobs to different
        # algorithms from 1 upload session, but that is not supported right now
        algorithm = session.algorithm_image.algorithm
        creator = session.creator

        experiment_url = reverse(
            "algorithms:execution-session-detail",
            kwargs={"slug": algorithm.slug, "pk": upload_session_pk},
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
            f"User: {creator.username}\n"
            f"Experiment ID: {upload_session_pk}"
        )

        for email in {
            creator.email,
            *[o.email for o in algorithm.editors_group.user_set.all()],
        }:
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
