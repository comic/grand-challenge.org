import uuid
from pathlib import Path

from celery import shared_task
from django.db.models import Q

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.backends.dockermachine.evaluator import (
    Evaluator,
)
from grandchallenge.evaluation.backends.dockermachine.utils import put_file
from grandchallenge.evaluation.models import Result
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
