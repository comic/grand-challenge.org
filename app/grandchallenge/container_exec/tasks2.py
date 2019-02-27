if __name__ == "__main__":
    from django import setup
    setup()

import time
import json
import datetime
import pytz
from grandchallenge.eyra_benchmarks.models import Submission
from grandchallenge.eyra_algorithms.models import Job, JobInput, Input
from grandchallenge.eyra_data.models import DataFile, get_data_file_name
from grandchallenge.container_exec.backends.k8s import K8sJob
from django.conf import settings


def create_algorithm_job(submission):
    job_attribute = "algorithm_job"
    output_file_name = "output_file"
    benchmark = submission.benchmark
    algorithm = submission.algorithm

    inputs = {
        "test_data": benchmark.test_data_file
    }

    return create_job(submission, algorithm, job_attribute, output_file_name, inputs)


def create_evaluation_job(submission):
    job_attribute = "evaluation_job"
    output_file_name = "metrics.json"
    benchmark = submission.benchmark
    algorithm = benchmark.evaluator

    inputs = {
        "predictions": submission.algorithm_job.output,
        "ground_truth": benchmark.test_ground_truth_data_file
    }

    return create_job(submission, algorithm, job_attribute, output_file_name, inputs)


def create_job(submission, algorithm, job_attribute, output_file_name, inputs):
    # Create an output file object
    output_file = DataFile(
        name=output_file_name,
        type=algorithm.interface.output_type
    )
    output_file.save()

    # Create a job object
    job = Job(algorithm=algorithm, output=output_file, status=Job.PENDING)
    job.save()

    for input_name, data_file in inputs.items():
        alg_input = algorithm.interface.inputs.get(name=input_name)
        job_input = JobInput(input=alg_input, data_file=data_file, job=job)
        job_input.save()

    setattr(submission, job_attribute, job)
    submission.save()
    return job.pk


def run_algorithm_job(job_pk):
    job_id_template = "algorithm-job-{}"
    return run_job(job_pk, job_id_template)


def run_evaluation_job(job_pk):
    job_id_template = "evaluation-job-{}"
    return run_job(job_pk, job_id_template)


def run_job(job_pk, job_id_template):
    s3_bucket = settings.AWS_STORAGE_BUCKET_NAME
    docker_registry_url = settings.PRIVATE_DOCKER_REGISTRY
    namespace = settings.K8S_NAMESPACE

    job = Job.objects.get(pk=job_pk)
    algorithm = job.algorithm
    output_file = job.output

    k8s_inputs = {}
    for jobinput in job.inputs.all():
        k8s_inputs[get_data_file_name(jobinput.data_file)] = jobinput.input.name

    # Set up input parameters for K8S job
    output_file_key = get_data_file_name(job.output)
    job_id = job_id_template.format(job_pk)
    image = f"{docker_registry_url}/{algorithm.container}"
    outputs = {output_file_key: "output_data"}  # HARD-CODED!

    # Define and execute K8S job
    k8s_job = K8sJob(
        job_id=job_id,
        namespace=namespace,
        image=image,
        s3_bucket=s3_bucket,
        inputs=k8s_inputs,
        outputs=outputs,
        blocking=False
    )
    k8s_job.execute()
    job.status = Job.STARTED
    job.started = datetime.datetime.now(pytz.timezone(settings.TIME_ZONE))
    job.save()

    # Poll K8S job for status
    while True:
        if k8s_job.succeeded or k8s_job.failed:
            break
        time.sleep(1)

    # Set EYRA Job properties
    job.stopped = datetime.datetime.now(pytz.timezone(settings.TIME_ZONE))
    job_success = False
    if k8s_job.succeeded:
        print("Job succeeded")
        job.status = Job.SUCCESS
        job_success = True
    elif k8s_job.failed:
        print("Job failed")
        job.status = Job.FAILURE
        k8s_job.print_logs()
    else:
        print("Unknown job status")
        print(k8s_job.status())
    job.log = json.dumps(k8s_job.get_logs())
    job.save()

    # Store output file key to django db
    output_file.file = output_file_key
    output_file.save()

    return job_success


if __name__ == "__main__":
    import sys
    submission = Submission.objects.all()[0]

    job_pk = create_algorithm_job(submission)
    success = run_algorithm_job(job_pk)
    if not success:
        sys.exit()


    job_pk = create_evaluation_job(submission)
    success = run_evaluation_job(job_pk)
