# -*- coding: utf-8 -*-
import uuid
from pathlib import Path

from celery import shared_task

from grandchallenge.algorithms.models import Job, Result
from grandchallenge.evaluation.backends.dockermachine.evaluator import \
    Evaluator


class AlgorithmExecutor(Evaluator):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            results_file=Path("/output/results.json"),
            **kwargs
        )


@shared_task
def execute_algorithm(*, job_pk: uuid.UUID):
    # TODO: error handling

    job = Job.objects.get(pk=job_pk)

    job.update_status(status=Job.STARTED)

    try:
        with AlgorithmExecutor(
                job_id=job_pk,
                input_files=[c.file for c in job.case.casefile_set.all()],
                eval_image=job.algorithm.image,
                eval_image_sha256=job.algorithm.image_sha256,
        ) as e:
            result = e.evaluate()
    except Exception as e:
        job.update_status(status=job.FAILURE, output=str(e))
        return

    Result.objects.create(job=job, output=result)
    job.update_status(status=Job.SUCCESS)
