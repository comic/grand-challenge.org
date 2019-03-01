# Only needed for standalone scripts
from django import setup
setup()
# End of standalone script stuff

import time
from grandchallenge.eyra_benchmarks.models import Submission
from grandchallenge.container_exec.backends.k8s_job_submission import create_algorithm_job
from grandchallenge.container_exec.tasks import run_and_evaluate_algorithm_task


if __name__ == "__main__":
    # Example code for spawning the K8S algorithm run and evaluation jobs
    #
    # Before starting, the following must be satisfied:
    # - the eyra-data-io Docker image should be present in the private Docker registry
    # - a Benchmark object must be present
    # - the test data and the ground truth data of the Benchmark should be present in the object store
    # - an Algorithm object must be present
    # - the Docker image that belongs to the Algorithm should be present in the private Docker registry
    # - a Submission object connecting the Benchmark and the Algorithm must be present

    # Retrieve the submission to process
    submission = Submission.objects.get(algorithm__name='Algorithm C')
    print("Submission", submission.algorithm.name)

    # Create a database Job for the submission algorithm container
    job_pk = create_algorithm_job(submission)

    # Run the submission algorithm job and evaluate the result using a Celery task
    celery_result = run_and_evaluate_algorithm_task.delay(job_pk)

    # Poll the task until ready
    while True:
        if celery_result.ready():
            break
        time.sleep(1)

    # Process results
    if celery_result.status == 'SUCCESS':
        # Reload database Submission object
        submission.refresh_from_db()

        # Print metrics
        print("Result:")
        print("---------")
        for k, v in submission.metrics_json.items():
            print(f"{k}: {v}")
