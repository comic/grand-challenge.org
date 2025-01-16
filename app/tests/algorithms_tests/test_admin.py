from pathlib import Path

import pytest
from django.core.files.base import ContentFile

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.tasks import create_algorithm_jobs
from grandchallenge.components.admin import requeue_jobs
from grandchallenge.components.models import ComponentInterface
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFileFactory
from tests.utils import recurse_callbacks


@pytest.mark.django_db
def test_job_updated_start_and_complete_times_after_admin_requeue(
    algorithm_image, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with django_capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image=None)

        with open(algorithm_image, "rb") as f:
            ai.image.save(algorithm_image, ContentFile(f.read()))

    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )
    ai.refresh_from_db()

    # Make sure the job fails when trying to upload an invalid file
    input_interface = ComponentInterface.objects.get(
        slug="generic-medical-image"
    )
    detection_interface = ComponentInterfaceFactory(
        store_in_database=False,
        relative_path="some_text.txt",
        slug="detection-json-file",
        kind=ComponentInterface.Kind.ANY,
    )
    ai.algorithm.inputs.add(input_interface)
    ai.algorithm.outputs.add(detection_interface)

    image_file = ImageFileFactory(
        file__from_path=Path(__file__).parent / "resources" / "input_file.tif"
    )

    civ = ComponentInterfaceValueFactory(
        image=image_file.image, interface=input_interface, file=None
    )

    with django_capture_on_commit_callbacks() as callbacks:
        create_algorithm_jobs(
            algorithm_image=ai,
            civ_sets=[{civ}],
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        )
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    jobs = Job.objects.filter(
        algorithm_image=ai, inputs__image=image_file.image, status=Job.FAILURE
    ).all()

    assert len(jobs) == 1

    job = jobs.first()

    first_run_started_at = job.started_at
    first_run_completed_at = job.completed_at

    with django_capture_on_commit_callbacks() as callbacks:
        requeue_jobs(None, None, jobs)

    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )
    job.refresh_from_db()

    second_run_started_at = job.started_at
    second_run_completed_at = job.completed_at

    assert second_run_started_at > first_run_started_at
    assert second_run_completed_at > first_run_completed_at
