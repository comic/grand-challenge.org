from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.db.transaction import on_commit

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.codebuild.client import CodeBuildClient
from grandchallenge.codebuild.models import Build


@shared_task()
def create_algorithm_image(*, pk):
    GitHubWebhookMessage = apps.get_model(  # noqa: N806
        app_label="github", model_name="GitHubWebhookMessage"
    )
    ghwm = GitHubWebhookMessage.objects.get(pk=pk)
    if Build.objects.filter(project_name=ghwm.project_name).exists():
        return
    algorithm = Algorithm.objects.get(
        repo_name=ghwm.payload["repository"]["full_name"]
    )

    client = CodeBuildClient(
        project_name=ghwm.project_name, msg=ghwm, algorithm=algorithm
    )
    client.create_build_project(
        source=f"{settings.PRIVATE_S3_STORAGE_KWARGS['bucket_name']}/{ghwm.zipfile.name}"
    )
    build_pk = client.start_build()
    on_commit(
        lambda: wait_for_build_completion.apply_async(
            kwargs={"build_pk": str(build_pk)}
        )
    )


@shared_task(bind=True, max_retries=100)
def wait_for_build_completion(self, *, build_pk):
    build = Build.objects.get(pk=build_pk)

    client = CodeBuildClient(build_id=build.build_id)

    status = client.get_build_status()
    if status == "IN_PROGRESS":
        self.retry(countdown=30)
    else:
        build.status = status
        build.build_log = client.get_logs()
        build.save()
        if status == "SUCCEEDED":
            on_commit(
                lambda: add_image_to_algorithm.apply_async(
                    kwargs={"build_pk": str(build_pk)}
                )
            )


@shared_task
def add_image_to_algorithm(*, build_pk):
    build = Build.objects.get(pk=build_pk)

    client = CodeBuildClient(
        project_name=build.project_name,
        algorithm=build.algorithm,
        msg=build.webhook_message,
    )
    client.add_image_to_algorithm()
