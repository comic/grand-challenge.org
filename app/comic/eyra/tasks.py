import json
from datetime import datetime
import time
from functools import reduce

import boto3
from celery import shared_task
from celery.bin.control import inspect
from django.conf import settings

from comic.container_exec.backends.k8s import K8sJob
from comic.eyra.models import Job, Submission, DataFile, JobInput


@shared_task
def run_job(job_pk):
    """Celery task for running a job.

    Args:
        job_pk: the primary key of the Job object that defines the algorithm run
    """
    job = Job.objects.get(pk=job_pk)
    if job.status != Job.PENDING:
        raise Exception(f"Can't start job with status '{Job.STATUS_CHOICES[job.status][1]}'")

    job.status = Job.STARTED
    job.started = datetime.now()
    job.save()

    job.log = ''
    try:
        with K8sJob(job) as k8s_job:
            k8s_job.run()

            # keep probing until failure or success
            while True:
                s = k8s_job.status()
                job.log = k8s_job.get_text_logs()
                job.save()

                if s.failed or s.succeeded:
                    break

                time.sleep(5)

            job.status = Job.SUCCESS if s.succeeded else Job.FAILURE
            job.log = k8s_job.get_text_logs()

    except Exception as e:
        job.status = Job.FAILURE
        job.log += '\n Error in job executor: \n' + str(e)
        raise e

    finally:
        job.stopped = datetime.now()
        job.save()

    if job.status == Job.FAILURE:
        raise Exception("Job failed")


# todo: fix for new db without implementation
def create_implementation_job_for_submission(submission: Submission):
    if submission.algorithm_job:
        raise Exception('Job already exists for submission')

    job_output = DataFile.objects.create(
        name='implementation job output',
        type=submission.benchmark.interface.output_type,
    )
    job_output.file = f"data_files/{str(job_output.pk)}"
    job_output.save()

    submission.algorithm_job = Job.objects.create(
        output=job_output,
        implementation=submission.implementation,
    )
    submission.save()

    input_data_file = submission.benchmark.data_set.public_test_data_file
    if submission.is_private:
        input_data_file = submission.benchmark.data_set.private_test_data_file

    job_input = JobInput.objects.create(
        job=submission.algorithm_job,
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
        data_file=submission.algorithm_job.output,
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
    tasks = reduce(lambda x, y: x + y, tasks_per_node)

    task_names = [task['name'] for task in tasks]

    scale_to = 0
    if run_submission.name in task_names:
        scale_to = 1

    print(f"Scaling to {str(scale_to)} GPU nodes.")

    print(autoscaling_client.set_desired_capacity(
        AutoScalingGroupName='terraform-eks-eyra-prod01-gpu',
        DesiredCapacity=scale_to
    ))