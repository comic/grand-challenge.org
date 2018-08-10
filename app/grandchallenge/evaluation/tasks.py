import uuid
from pathlib import Path

from celery import shared_task
from django.db.models import Q
from django.utils.module_loading import import_string

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.tasks import get_model_instance, create_result
from grandchallenge.evaluation.backends.dockermachine.evaluator import (
    Evaluator,
)
from grandchallenge.evaluation.backends.dockermachine.utils import put_file
from grandchallenge.evaluation.exceptions import EvaluationException
from grandchallenge.evaluation.models import Job, Result
from grandchallenge.evaluation.utils import generate_rank_dict
from grandchallenge.evaluation.validators import get_file_mimetype


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
        result_object_output_kwarg: str,
        evaluation_class: str,
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
        msg = f"Method {job.method.id} was not ready to be used."
        job.update_status(status=Job.FAILURE, output=msg, )
        raise AttributeError(msg)

    try:
        Evaluator = import_string(evaluation_class)
    except ImportError:
        job.update_status(
            status=Job.FAILURE, output=f"Could not import {evaluation_class}.",
        )
        raise

    try:
        with Evaluator(
                job_id=job.pk,
                input_files=(job.submission.file,),
                eval_image=job.method.image,
                eval_image_sha256=job.method.image_sha256,
        ) as e:
            result = e.evaluate()  # This call is potentially very long

    except EvaluationException as exc:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(status=Job.FAILURE, output=exc.message)
        raise

    create_result(
        job_pk=job_pk,
        job_app_label=job_app_label,
        job_model_name=job_model_name,
        result_app_label=result_app_label,
        result_model_name=result_model_name,
        **{result_object_output_kwarg: result},
    )

    return result


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
