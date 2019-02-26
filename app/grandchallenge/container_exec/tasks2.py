if __name__ == "__main__":
    from django import setup
    setup()

import time
import json
import datetime
import pytz
from grandchallenge.eyra_benchmarks.models import Submission, Job
from grandchallenge.eyra_data.models import DataFile, get_data_file_name
from grandchallenge.container_exec.backends.k8s import K8sJob
from django.conf import settings


def run_algorithm():
    # INPUTS
    submission = Submission.objects.all()[0]
    namespace = "dev-roel"
    docker_registry_url = "docker-registry.roel.dev.eyrabenchmark.net"
    s3_bucket = "eyra-datasets"

    benchmark = submission.benchmark
    algorithm = submission.algorithm
    job_attribute = "algorithm_job"
    job_id_template = "submission-job-{}"

    input_file_keys = [get_data_file_name(benchmark.test_data_file)]
    input_file_names = ["test_data_file"]
    inputs = dict(zip(input_file_keys, input_file_names))
    output_file_name = "output_file"
    # END OF INPUTS

    create_and_run_job(
        submission,
        namespace,
        docker_registry_url,
        s3_bucket,
        algorithm,
        job_attribute,
        job_id_template,
        inputs,
        output_file_name
    )

def run_evaluation():
    # INPUTS
    submission = Submission.objects.all()[0]
    namespace = "dev-roel"
    docker_registry_url = "docker-registry.roel.dev.eyrabenchmark.net"
    s3_bucket = "eyra-datasets"

    benchmark = submission.benchmark
    algorithm = benchmark.evaluator
    job_attribute = "evaluation_job"
    job_id_template = "evaluation-job-{}"

    input_file_keys = [get_data_file_name(submission.algorithm_job.output), get_data_file_name(benchmark.test_ground_truth_data_file)]
    input_file_names = ["prediction", "ground_truth"]
    inputs = dict(zip(input_file_keys, input_file_names))
    output_file_name = "metrics.json"
    # END OF INPUTS

    create_and_run_job(
        submission,
        namespace,
        docker_registry_url,
        s3_bucket,
        algorithm,
        job_attribute,
        job_id_template,
        inputs,
        output_file_name
    )


def create_and_run_job(
        submission,
        namespace,
        docker_registry_url,
        s3_bucket,
        algorithm,
        job_attribute,
        job_id_template,
        inputs,
        output_file_name
    ):

    # Create an output file object
    output_file = DataFile(
        name=output_file_name,
        type=algorithm.interface.output_type
    )
    output_file.save()

    # Create a job object
    job = Job(algorithm=algorithm, output=output_file, status=Job.PENDING)
    job.save()
    setattr(submission, job_attribute, job)
    submission.save()

    # Set up input parameters for K8S job
    output_file_key = get_data_file_name(output_file)
    job_id = job_id_template.format(job.pk)
    image = f"{docker_registry_url}/{algorithm.container}"
    outputs = {output_file_key: output_file.name}

    # Define and execute K8S job
    k8s_job = K8sJob(
        job_id=job_id,
        namespace=namespace,
        image=image,
        s3_bucket=s3_bucket,
        inputs=inputs,
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
    if k8s_job.succeeded:
        job.status = Job.SUCCESS
    elif k8s_job.failed:
        job.status = Job.FAILURE
    else:
        print("Unknown job status")
        print(k8s_job.status())
    job.log = json.dumps(k8s_job.get_logs())
    job.save()

    # Store output file key to django db
    output_file.file = output_file_key
    output_file.save()




if __name__ == "__main__":
    run_algorithm()
    run_evaluation()