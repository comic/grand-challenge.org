import json
import boto3

from django.conf import settings

from celery import shared_task
from celery.task.control import inspect
from functools import reduce

from comic.eyra_algorithms.models import Job, JobInput
from comic.eyra_algorithms.tasks import run_job
from comic.eyra_benchmarks.models import Submission
from comic.eyra_data.models import DataFile, DataType


def create_implementation_job_for_submission(submission: Submission):
    if submission.implementation_job:
        raise Exception('Job already exists for submission')

    job_output = DataFile.objects.create(
        name='implementation job output',
        type=submission.benchmark.interface.output_type,
    )
    job_output.file = f"data_files/{str(job_output.pk)}"
    job_output.save()

    submission.implementation_job = Job.objects.create(
        output=job_output,
        implementation=submission.implementation,
    )
    submission.save()

    input_data_file = submission.benchmark.data_set.public_test_data_file
    if submission.is_private:
        input_data_file = submission.benchmark.data_set.private_test_data_file

    job_input = JobInput.objects.create(
        job=submission.implementation_job,
        input=submission.benchmark.interface.inputs.first(),
        data_file=input_data_file,
    )


def create_evaluation_job_for_submission(submission: Submission):
    if submission.evaluation_job:
        raise Exception('Job already exists for submission')

    interface = submission.benchmark.evaluator.algorithm.interface
    
    job_output = DataFile.objects.create(
        name='evaluation job output',
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

    ground_truth_data_file = submission.benchmark.data_set.public_ground_truth_data_file
    if submission.is_private:
        ground_truth_data_file = submission.benchmark.data_set.private_ground_truth_data_file

    job_ground_truth_input = JobInput.objects.create(
        job=submission.evaluation_job,
        input=interface.inputs.get(name='ground_truth'),
        data_file=ground_truth_data_file,
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
    try:
        eval_output = submission.evaluation_job.output.file.read().decode('ascii')
        submission.metrics = json.loads(eval_output)['metrics']
    except:
        submission.metrics = "Error getting 'metrics' value from evaluation output."
    submission.save()


@shared_task
def autoscale_gpu_node():
    autoscaling_client = boto3.client(
        'autoscaling',
        region_name=settings.AWS_AUTOSCALING_REGION,
        aws_access_key_id=settings.AWS_AUTOSCALING_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_AUTOSCALING_SECRET_ACCESS_KEY,
    )

    i = inspect()
    active_tasks_per_node = [a[1] for a in list(i.active().items())]
    scheduled_tasks_per_node = [a[1] for a in list(i.scheduled().items())]
    reserved_tasks_per_node = [a[1] for a in list(i.reserved().items())]

    tasks_per_node = active_tasks_per_node + scheduled_tasks_per_node + reserved_tasks_per_node
    tasks = reduce(lambda x, y: x+y, tasks_per_node)

    task_names = [task['name'] for task in tasks]

    scale_to = 0
    if run_submission.name in task_names:
        scale_to = 1

    print(f"Scaling to {str(scale_to)} GPU nodes.")

    autoscaling_client.set_desired_capacity(
        AutoScalingGroupName='terraform-eks-eyra-prod01-gpu',
        DesiredCapacity=scale_to
    )