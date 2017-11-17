import uuid

from celery import shared_task

from evaluation.backends.dockermachine.evaluator import Evaluator
from evaluation.models import Job, Result
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

    try:
        with Evaluator(
                job_id=job.pk,
                input_file=job.submission.file,
                eval_image=job.method.image,
                eval_image_sha256=job.method.image_sha256
        ) as e:
            result = e.evaluate()
    except Exception as exc:
        job.update_status(status=Job.FAILURE, output=str(exc))
        raise exc

    Result.objects.create(
        user=job.submission.user,
        challenge=job.submission.challenge,
        method=job.method,
        metrics=result
    )

    job.update_status(status=Job.SUCCESS)

    return result


@shared_task
def cleanup_stale_uploads(*_):
    cleanup_stale_files()
