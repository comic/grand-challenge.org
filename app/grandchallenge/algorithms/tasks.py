from celery import shared_task

from grandchallenge.algorithms.models import DEFAULT_INPUT_INTERFACE_SLUG, Job
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


@shared_task
def create_algorithm_jobs(*_, upload_session_pk):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)

    default_input_interface = ComponentInterface.objects.get(
        slug=DEFAULT_INPUT_INTERFACE_SLUG
    )

    for image in session.image_set.all():
        j = Job.objects.create(
            creator=session.creator, algorithm_image=session.algorithm_image,
        )
        j.inputs.set(
            [
                ComponentInterfaceValue.objects.create(
                    interface=default_input_interface, image=image
                )
            ]
        )
        j.schedule_job()
