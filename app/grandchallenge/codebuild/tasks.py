from celery import shared_task
from django.apps import apps
from django.conf import settings

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.codebuild.client import CodeBuildClient


@shared_task()
def create_algorithm_image(*, pk):
    GitHubWebhookMessage = apps.get_model(  # noqa: N806
        app_label="github", model_name="GitHubWebhookMessage"
    )
    ghwm = GitHubWebhookMessage.objects.get(pk=pk)

    client = CodeBuildClient(project_name=ghwm.project_name)
    client.create_build_project(
        source=f"{settings.PRIVATE_S3_STORAGE_KWARGS['bucket_name']}/{ghwm.zipfile.name}"
    )
    client.start_build()

    status = client.wait_for_completion()
    if status != "SUCCEEDED":
        return
    algorithm = Algorithm.objects.get(
        repo_name=ghwm.payload["repository"]["full_name"]
    )
    client.add_image_to_algorithm(algorithm=algorithm)
