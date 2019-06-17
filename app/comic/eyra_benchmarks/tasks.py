from celery import shared_task

from comic.eyra_algorithms.models import Job, JobInput
from comic.eyra_algorithms.tasks import run_job
from comic.eyra_benchmarks.models import Submission
from comic.eyra_data.models import DataFile, DataType


def create_implementation_job_for_submission(submission: Submission):
    if submission.implementation_job:
        raise Exception('Job already exists for submission')

    job_output = DataFile.objects.create(
        name='output',
        type=submission.benchmark.interface.output_type,
    )
    job_output.file = f"data_files/{str(job_output.pk)}"
    job_output.save()

    submission.implementation_job = Job.objects.create(
        output=job_output,
        implementation=submission.implementation,
    )
    submission.save()

    job_input = JobInput.objects.create(
        job=submission.implementation_job,
        input=submission.benchmark.interface.inputs.first(),
        data_file=submission.benchmark.data_set.test_data_file,
    )


def create_evaluation_job_for_submission(submission: Submission):
    if submission.evaluation_job:
        raise Exception('Job already exists for submission')

    interface = submission.benchmark.evaluator.algorithm.interface
    
    job_output = DataFile.objects.create(
        name='output',
        type=interface.output_type,
    )
    job_output.file = f"data_files/{str(job_output.pk)}"
    job_output.save()

    submission.evaluation_job = Job.objects.create(
        output=job_output,
        implementation=submission.benchmark.evaluator,
    )
    submission.save()

    job_implementation_output_input = JobInput.objects.create(
        job=submission.evaluation_job,
        input=interface.inputs.get(name='implementation_output'),
        data_file=submission.implementation_job.output,
    )

    job_ground_truth_input = JobInput.objects.create(
        job=submission.evaluation_job,
        input=interface.inputs.get(name='ground_truth'),
        data_file=submission.benchmark.data_set.test_ground_truth_data_file,
    )


@shared_task
def run_submission(submission_pk):
    submission = Submission.objects.get(pk=submission_pk)
    create_implementation_job_for_submission(submission)
    create_evaluation_job_for_submission(submission)

    try:
        run_job(submission.implementation_job.pk)
    except Exception as e:
        submission.evaluation_job.status = Job.FAILURE
        submission.evaluation_job.log = 'Cannot evaluate, since the implementation job failed.'
        submission.evaluation_job.save()
        raise e

    run_job(submission.evaluation_job.pk)
    submission.metrics_json = submission.evaluation_job.output.file.read().decode('ascii')
    submission.save()

