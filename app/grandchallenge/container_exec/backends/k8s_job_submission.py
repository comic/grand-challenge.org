import time
import json
import datetime
import pytz

from django.conf import settings

from grandchallenge.eyra_algorithms.models import Job, JobInput
from grandchallenge.eyra_data.models import DataFile, get_data_file_name
from grandchallenge.container_exec.backends.k8s import K8sJob


def create_algorithm_job(submission):
    """Convenience wrapper around create_job for algorithm containers.

    Args:
        submission (eyra_benchmarks.models.Submission): the submission to create an algorithm job for
    """

    job_attribute = "algorithm_job"
    output_file_name = "output_file"
    benchmark = submission.benchmark
    algorithm = submission.algorithm

    inputs = {
        "test_data": benchmark.test_data_file
    }

    return create_job(submission, algorithm, job_attribute, output_file_name, inputs)


def create_evaluation_job(submission):
    """Convenience wrapper around create_job for evaluation containers.

    Args:
        submission (eyra_benchmarks.models.Submission): the submission to create an evaluation job for
    """

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
    """Create a job used in the submission algorithm/evaluation workflow.

    Starts a job for the given algorithm (either an algorithm or an evaluation).

    Args:
        submission (eyra_benchmarks.models.Submission): the submission to create a job for.
        algorithm (eyra_algorithms.models.Algorithm): the algorithm to run in the job
        job_attribute (string): the submission attribute name of the job that is to be created (either "algorithm_job" or "evaluation_job")
        output_file_name (string): the file name of the algorithm output, relative to the output folder (/output)
        inputs (dict): a dict of (filename, FileField) pairs defining the inputs

    Returns:
        the primary key of the job object that is created
    """
    # Create an empty output DataFile object
    output_file = DataFile(
        name=output_file_name,
        type=algorithm.interface.output_type
    )
    output_file.save()

    # Create a pending Job object that links to the empty output FileObject
    job = Job(algorithm=algorithm, output=output_file, status=Job.PENDING)
    job.save()

    # Set up the JobInputs for the Job based on the Algorithm's Interface
    for input_name, data_file in inputs.items():
        alg_input = algorithm.interface.inputs.get(name=input_name)
        job_input = JobInput(input=alg_input, data_file=data_file, job=job)
        job_input.save()

    # Add the Job to the Submission object
    setattr(submission, job_attribute, job)
    submission.save()

    return job.pk


def run_algorithm_job(job_pk):
    """Convenience wrapper around run_job for running algorithm jobs."""
    job_id = f"algorithm-job-{job_pk}"
    return run_job(job_pk, job_id)


def run_evaluation_job(job_pk):
    """Convenience function around run_job for running evaluation jobs."""
    job_id = f"evaluation-job-{job_pk}"
    return run_job(job_pk, job_id)


def run_job(job_pk, job_id):
    """Creates and executes a K8S job based on the information in the given Job object.

    Args:
        job_pk: the primary key of the job to execute
        job_id (str): the name to be used for the K8S job name
    """

    # Retrieve settings
    s3_bucket = settings.AWS_STORAGE_BUCKET_NAME
    docker_registry_url = settings.PRIVATE_DOCKER_REGISTRY
    namespace = settings.K8S_NAMESPACE

    # Retrieve the Job, Algorithm and output DataFile objects
    job = Job.objects.get(pk=job_pk)
    algorithm = job.algorithm
    output_file = job.output

    # Collect the algorithm input DataFile info into a dict
    k8s_inputs = {}
    for jobinput in job.inputs.all():
        k8s_inputs[get_data_file_name(jobinput.data_file)] = jobinput.input.name

    # Collect the algorithm output DataFile info into a dict
    output_file_key = get_data_file_name(job.output)
    outputs = {output_file_key: "output_data"}  # TODO: Local file name in container is hard-coded

    image = f"{docker_registry_url}/{algorithm.container}"

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

    # Update the Job object
    job.status = Job.STARTED
    job.started = datetime.datetime.now(pytz.timezone(settings.TIME_ZONE))
    job.save()

    # Poll K8S job for status until completion
    while True:
        if k8s_job.succeeded or k8s_job.failed:
            break
        time.sleep(1)

    # Update the Job object
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

    # Store output file object key in the output DataFile object
    output_file.file = output_file_key
    output_file.save()

    return job_success

