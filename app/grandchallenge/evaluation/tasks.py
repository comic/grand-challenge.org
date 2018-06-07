import uuid
from pathlib import Path

from celery import shared_task
from django.apps import apps
from django.db import OperationalError
from django.db.models import Q

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.backends.dockermachine.evaluator import (
    Evaluator,
)
from grandchallenge.evaluation.backends.dockermachine.utils import put_file
from grandchallenge.evaluation.exceptions import EvaluationException
from grandchallenge.evaluation.models import Job, Result
from grandchallenge.evaluation.utils import generate_rank_dict
from grandchallenge.evaluation.validators import get_file_mimetype


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


@retry_if_dropped
def create_result(
        *,
        metrics,
        job_pk,
        job_app_label,
        job_model_name,
        result_app_label,
        result_model_name
):
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )

    # Note: assumes that the result and job classes are in the same app
    result_model = apps.get_model(
        app_label=result_app_label, model_name=result_model_name
    )

    result_model.objects.create(
        job=job, metrics=metrics, challenge=job.challenge
    )

    job.update_status(status=Job.SUCCESS)


class SubmissionEvaluator(Evaluator):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            results_file=Path("/output/metrics.json"),
            **kwargs,
        )

    def _copy_input_files(self, writer):
        for file in self._input_files:
            dest_file = '/tmp/submission-src'
            put_file(
                container=writer, src=file, dest=dest_file
            )

            with file.open('rb') as f:
                mimetype = get_file_mimetype(f)

            if mimetype.lower() == 'application/zip':
                # Unzip the file in the container rather than in the python
                # process. With resource limits this should provide some
                # protection against zip bombs etc.
                writer.exec_run(f'unzip {dest_file} -d /input/')
            else:
                # Not a zip file, so must be a csv
                writer.exec_run(f'mv {dest_file} /input/submission.csv')


@shared_task
def evaluate_submission(
        *,
        job_pk: uuid.UUID,
        job_app_label: str,
        job_model_name: str,
        result_app_label: str,
        result_model_name: str,
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
    job.update_status(status=Job.STARTED)

    if not job.method.ready:
        job.update_status(
            status=Job.FAILURE,
            output=f"Method {job.method.id} was not ready to be used.",
        )
        return {}

    try:
        with SubmissionEvaluator(
                job_id=job.pk,
                input_files=(job.submission.file,),
                eval_image=job.method.image,
                eval_image_sha256=job.method.image_sha256,
        ) as e:
            metrics = e.evaluate()  # This call is potentially very long
    except EvaluationException as exc:
        job = get_model_instance(
            job_pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(status=Job.FAILURE, output=exc.message)
        return {}

    create_result(
        metrics=metrics,
        job_pk=job_pk,
        job_app_label=job_app_label,
        job_model_name=job_model_name,
        result_app_label=result_app_label,
        result_model_name=result_model_name,
    )

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
