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
from grandchallenge.subdomains.utils import reverse


@shared_task
def create_algorithm_jobs(*_, upload_session_pk):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)

    default_input_interface = ComponentInterface.objects.get(
        slug=DEFAULT_INPUT_INTERFACE_SLUG
    )

    jobs = []

    if session.creator and session.algorithm_image:
        for image in session.image_set.all():
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

    workflow = group(*jobs) | send_experiment_complete_email.signature(
        upload_session_pk=upload_session_pk
    )
    workflow.apply_async()


@shared_task
def send_experiment_complete_email(*_, upload_session_pk):
    jobs = Job.objects.filter(
        inputs__image__origin_id=upload_session_pk
    ).distinct()

    failed_jobs = jobs.filter(status=Job.FAILURE).count()

    if failed_jobs:
        algorithm = jobs[0].algorithm_image.algorithm
        creator = jobs[0].creator

        experiments_url = reverse(
            "algorithms:execution-session-list",
            kwargs={"slug": algorithm.slug},
        )

        message = (
            f"Unfortunately {failed_jobs} of your jobs for algorithm "
            f"'{algorithm.title}' failed with an error. "
            f"You can inspect the output and error messages at "
            f"{experiments_url}.\n\n"
            f"You may wish to try and correct these errors and try again, "
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
                    f"Jobs failed"
                ),
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
