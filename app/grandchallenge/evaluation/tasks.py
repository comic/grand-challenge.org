import uuid

from celery import shared_task
from django.db import OperationalError
from django.db.models import Q

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.backends.dockermachine.evaluator import (
    Evaluator,
)
from grandchallenge.evaluation.exceptions import EvaluationException
from grandchallenge.evaluation.models import Job, Result
from grandchallenge.evaluation.utils import generate_rank_dict


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
def get_job(*, job_pk) -> Job:
    return Job.objects.get(pk=job_pk)


@retry_if_dropped
def create_result(*, metrics, job_pk):
    job = get_job(job_pk=job_pk)
    Result.objects.create(job=job, metrics=metrics, challenge=job.challenge)
    job.update_status(status=Job.SUCCESS)


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
            job_pk is not None and job is not None
    ):
        raise TypeError(
            'You need to provide either a job or a job_id as '
            'arguments to evaluate_submission, not none or both.'
        )

    if job:
        job_pk = job.pk

    job = get_job(job_pk=job_pk)
    job.update_status(status=Job.STARTED)

    if not job.method.ready:
        # TODO: email admin
        job.update_status(
            status=Job.FAILURE,
            output=f"Method {job.method.id} was not ready to be used.",
        )
        return {}

    try:
        with Evaluator(
                job_id=job.pk,
                input_file=job.submission.file,
                eval_image=job.method.image,
                eval_image_sha256=job.method.image_sha256,
        ) as e:
            metrics = e.evaluate()  # This call is potentially very long
    except EvaluationException as exc:
        job = get_job(job_pk=job_pk)
        job.update_status(status=Job.FAILURE, output=exc.message)
        return {}

    create_result(metrics=metrics, job_pk=job_pk)

    return metrics


@shared_task
def calculate_ranks(*, challenge_pk: uuid.UUID):
    challenge = Challenge.objects.get(pk=challenge_pk)
    valid_results = Result.objects.filter(
        Q(challenge=challenge), Q(public=True)
    )
    ranks = generate_rank_dict(
        queryset=valid_results,
        metric_paths=(challenge.evaluation_config.score_jsonpath,),
        metric_reverse=(
            challenge.evaluation_config.score_default_sort ==
            challenge.evaluation_config.DESCENDING,
        ),
    )
    for res in Result.objects.filter(Q(challenge=challenge)):
        try:
            rank = ranks[str(res.pk)][
                challenge.evaluation_config.score_jsonpath
            ]
        except KeyError:
            rank = 0
        Result.objects.filter(pk=res.pk).update(rank=rank)
    return ranks
