import json
import tarfile
import uuid

from celery import shared_task
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import OperationalError

from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.eyra_benchmarks.models import Submission
from grandchallenge.eyra_algorithms.models import Job
from grandchallenge.container_exec.backends.k8s_job_submission import (
    run_algorithm_job, run_evaluation_job, create_evaluation_job
)


@shared_task
def run_and_evaluate_algorithm_task(algorithm_job_pk):
    """Celery task for executing and evaluting algorithm submissions.

    Args:
        algorith_job_pk: the primary key of the Job object that defines the algorithm run
    """
    algorithm_job = Job.objects.get(pk=algorithm_job_pk)
    submission = Submission.objects.get(algorithm_job=algorithm_job)

    print(f"Starting algorithm job {algorithm_job_pk}")
    success = run_algorithm_job(algorithm_job_pk)
    if not success:
        # Set task status etc
        return

    evaluation_job_pk = create_evaluation_job(submission)
    print(f"Starting evaluation job {evaluation_job_pk}")
    success = run_evaluation_job(evaluation_job_pk)
    if not success:
        # Set task status etc
        return

    # Make sure we have the evaluation job and an up-to-date version of the submission
    evaluation_job = Job.objects.get(pk=evaluation_job_pk)
    submission.refresh_from_db()

    # Retrieve and store the metrics
    metrics_json = json.load(evaluation_job.output.file)
    submission.metrics_json = metrics_json
    submission.save()


@shared_task()
def validate_docker_image_async(
    *, pk: uuid.UUID, app_label: str, model_name: str
):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    instance = model.objects.get(pk=pk)

    if not instance.image:
        # Create the image from the staged file
        uploaded_image = StagedAjaxFile(instance.staged_image_uuid)
        with uploaded_image.open() as f:
            instance.image.save(uploaded_image.name, File(f))

    try:
        with instance.image.open(mode="rb") as im, tarfile.open(
            fileobj=im, mode="r"
        ) as t:
            member = dict(zip(t.getnames(), t.getmembers()))["manifest.json"]
            manifest = t.extractfile(member).read()
    except (KeyError, tarfile.ReadError):
        model.objects.filter(pk=pk).update(
            status=(
                "manifest.json not found at the root of the container image file. "
                "Was this created with docker save?"
            )
        )
        raise ValidationError("Invalid Dockerfile")

    manifest = json.loads(manifest)

    if len(manifest) != 1:
        model.objects.filter(pk=pk).update(
            status=(
                f"The container image file should only have 1 image. "
                f"This file contains {len(manifest)}."
            )
        )
        raise ValidationError("Invalid Dockerfile")

    model.objects.filter(pk=pk).update(
        image_sha256=f"sha256:{manifest[0]['Config'][:64]}", ready=True
    )


def retry_if_dropped(func):
    """
    Sometimes the Mysql connection will drop for long running jobs. This is
    a decorator that will retry a function that relies on a usable connection.
    """

    def wrapper(*args, **kwargs):
        n_tries = 0
        max_tries = 2
        err = None

        while n_tries < max_tries:
            n_tries += 1

            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                err = e

                # This needs to be a local import
                from django.db import connection

                connection.close()

        raise err

    return wrapper


@retry_if_dropped
def get_model_instance(*, pk, app_label, model_name):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    return model.objects.get(pk=pk)


@shared_task
def execute_job(
    *, job_pk: uuid.UUID, job_app_label: str, job_model_name: str
) -> dict:
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    job.update_status(status=job.STARTED)

    if not job.container.ready:
        msg = f"Method {job.container.pk} was not ready to be used."
        job.update_status(status=job.FAILURE, output=msg)
        raise RuntimeError(msg)

    try:
        with job.executor_cls(
            job_id=job.pk,
            input_files=job.input_files,
            exec_image=job.container.image,
            exec_image_sha256=job.container.image_sha256,
        ) as ev:
            result = ev.execute()  # This call is potentially very long

    except Exception as exc:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(status=job.FAILURE, output=str(exc))
        raise

    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    job.create_result(result=result)
    job.update_status(status=job.SUCCESS)

    return result
