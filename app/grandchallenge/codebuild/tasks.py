from celery import shared_task
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import on_commit

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage


@shared_task()
def create_codebuild_build(*, pk):
    GitHubWebhookMessage = apps.get_model(  # noqa: N806
        app_label="github", model_name="GitHubWebhookMessage"
    )
    ghwm = GitHubWebhookMessage.objects.get(pk=pk)

    Build = apps.get_model(  # noqa: N806
        app_label="codebuild", model_name="Build"
    )

    if Build.objects.filter(webhook_message=ghwm).exists():
        # Build already exists
        return

    try:
        algorithm = Algorithm.objects.get(
            repo_name=ghwm.payload["repository"]["full_name"]
        )
    except ObjectDoesNotExist:
        # Repository is not linked to algorithm
        return

    algorithm_image = AlgorithmImage.objects.create(
        algorithm=algorithm,
        requires_gpu=algorithm.image_requires_gpu,
        requires_memory_gb=algorithm.image_requires_memory_gb,
    )

    build = Build.objects.create(
        webhook_message=ghwm, algorithm_image=algorithm_image,
    )

    on_commit(
        lambda: wait_for_build_completion.apply_async(
            kwargs={"build_pk": str(build.pk)}
        )
    )


@shared_task(bind=True, max_retries=120)
def wait_for_build_completion(self, *, build_pk):
    Build = apps.get_model(  # noqa: N806
        app_label="codebuild", model_name="Build"
    )

    build = Build.objects.get(pk=build_pk)
    build.refresh_status()

    if build.status == build.BuildStatusChoices.IN_PROGRESS:
        self.retry(countdown=30)
    else:
        build.refresh_logs()
        build.save()
        if build.status == build.BuildStatusChoices.SUCCEEDED:
            on_commit(
                lambda: add_image_to_algorithm.apply_async(
                    kwargs={"build_pk": str(build_pk)}
                )
            )


@shared_task
def add_image_to_algorithm(*, build_pk):
    Build = apps.get_model(  # noqa: N806
        app_label="codebuild", model_name="Build"
    )

    build = Build.objects.get(pk=build_pk)
    build.add_image_to_algorithm()
