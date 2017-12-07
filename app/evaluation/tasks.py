import json
import tarfile
import uuid

from celery import shared_task

from evaluation.backends.dockermachine.evaluator import Evaluator
from evaluation.models import Job, Result, Method
from evaluation.widgets.uploader import cleanup_stale_files


@shared_task
def evaluate_submission(*, job_pk: uuid.UUID = None, job: Job = None) -> dict:
    """
    Interfaces between Django and the Evaluation. Gathers together all
    resources, and then writes the result back to the database so that the
    Evaluation is only concerned with producing metrics.json.

    :param job_pk:
        The id of the job. This must be a str or UUID as celery cannot
        serialise Job objects to JSON.
    :return:
    """

    if (job_pk is None and job is None) or (
                    job_pk is not None and job is not None):
        raise TypeError('You need to provide either a job or a job_id as '
                        'arguments to evaluate_submission, not none or both.')

    if job_pk:
        job = Job.objects.get(pk=job_pk)  # type: Job

    job.update_status(status=Job.STARTED)

    if not job.method.ready:
        # TODO: email admin
        job.update_status(status=Job.FAILURE,
                          output=f"Method {job.method.id} was not ready to be used.")
        return {}

    try:
        with Evaluator(
                job_id=job.pk,
                input_file=job.submission.file,
                eval_image=job.method.image,
                eval_image_sha256=job.method.image_sha256
        ) as e:
            metrics = e.evaluate()
    except Exception as exc:
        job.update_status(status=Job.FAILURE, output=str(exc))
        raise exc

    Result.objects.create(job=job, metrics=metrics, challenge=job.challenge)

    job.update_status(status=Job.SUCCESS)

    return metrics


@shared_task()
def validate_method_async(*, method_pk: uuid.UUID = None):
    instance = Method.objects.get(pk=method_pk)

    instance.image.open(mode='rb')

    try:
        with tarfile.open(fileobj=instance.image, mode='r') as t:
            member = dict(zip(t.getnames(), t.getmembers()))[
                'manifest.json']
            manifest = t.extractfile(member).read()
    except KeyError:
        instance.status = 'manifest.json not found at the root of the ' \
                          'container image file. Was this created ' \
                          'with docker save?'
        instance.save()
        # TODO: email admin
        return

    manifest = json.loads(manifest)
    if len(manifest) != 1:
        instance.status = 'The container image file should only have ' \
                          '1 image. This file contains ' \
                          f'{len(manifest)}.'
        instance.save()
        # TODO: email admin
        return

    instance.image_sha256 = f"sha256:{manifest[0]['Config'][:64]}"
    instance.ready = True
    instance.save()


@shared_task
def cleanup_stale_uploads():
    cleanup_stale_files()
