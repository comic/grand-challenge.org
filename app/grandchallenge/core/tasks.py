import json
import tarfile
import uuid

from celery import shared_task
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import OperationalError

from grandchallenge.evaluation.exceptions import EvaluationException


@shared_task
def clear_sessions():
    """ Clear the expired sessions stored in django_session """
    call_command('clearsessions')


@shared_task()
def validate_docker_image_async(
        *, pk: uuid.UUID, app_label: str, model_name: str
):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    instance = model.objects.get(pk=pk)
    instance.image.open(mode='rb')

    try:
        with tarfile.open(fileobj=instance.image, mode='r') as t:
            member = dict(zip(t.getnames(), t.getmembers()))['manifest.json']
            manifest = t.extractfile(member).read()
    except (KeyError, tarfile.ReadError):
        model.objects.filter(pk=pk).update(status=(
            'manifest.json not found at the root of the container image file. '
            'Was this created with docker save?'
        ))
        raise ValidationError("Invalid Dockerfile")

    manifest = json.loads(manifest)

    if len(manifest) != 1:
        model.objects.filter(pk=pk).update(status=(
            f'The container image file should only have 1 image. '
            f'This file contains {len(manifest)}.'
        ))
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
        *, job_pk: uuid.UUID, job_app_label: str, job_model_name: str,
) -> dict:
    """
    Interfaces between Django and the Evaluation. Gathers together all
    resources, and then writes the result back to the database so that the
    Evaluation is only concerned with producing metrics.json.

    :param job_pk:
        The id of the job. This must be a str or UUID as celery cannot
        serialise Job objects to JSON.
    :return:
    """

    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    job.update_status(status=job.STARTED)

    if not job.container.ready:
        msg = f"Method {job.container.pk} was not ready to be used."
        job.update_status(status=job.FAILURE, output=msg, )
        raise AttributeError(msg)

    try:
        with job.evaluator_cls(
                job_id=job.pk,
                input_files=job.input_files,
                eval_image=job.container.image,
                eval_image_sha256=job.container.image_sha256,
        ) as e:
            result = e.evaluate()  # This call is potentially very long

    except EvaluationException as exc:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(status=job.FAILURE, output=exc.message)
        raise

    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    job.create_result(result=result)
    job.update_status(status=job.SUCCESS)

    return result
