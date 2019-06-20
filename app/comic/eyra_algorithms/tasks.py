from datetime import datetime
import time
from functools import reduce

import boto3
from celery import shared_task
from celery.task.control import inspect

from comic.container_exec.backends.k8s import K8sJob
from comic.eyra_algorithms.models import Job
from comic.eyra_benchmarks.tasks import run_submission

from django.conf import settings

@shared_task
def autoscale_gpu_node():
    autoscaling_client = boto3.client(
        'autoscaling',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
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
