from django import setup
setup()
from grandchallenge.eyra_benchmarks.models import Submission
from grandchallenge.container_exec.backends.k8s_job_submission import create_submission_job


submission = Submission.objects.get(algorithm__name='Algorithm C')
print("Submission", submission.algorithm.name)
celery_result = create_submission_job(submission)

while True:
    if celery_result.ready():
        break

print(celery_result.status)
print(celery_result.result)
