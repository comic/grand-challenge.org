from datetime import datetime
import time

from celery import shared_task

from comic.container_exec.backends.k8s import K8sJob
from comic.eyra_algorithms.models import Job



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
