from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.transaction import on_commit

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage
from grandchallenge.components.tasks import _retry


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
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

    with transaction.atomic():
        algorithm_image = AlgorithmImage.objects.create(
            algorithm=algorithm,
            requires_gpu=algorithm.image_requires_gpu,
            requires_memory_gb=algorithm.image_requires_memory_gb,
        )
        build = Build.objects.create(
            webhook_message=ghwm, algorithm_image=algorithm_image
        )

        # TODO rather than waiting for completion use CloudWatch events

        on_commit(
            lambda: wait_for_build_completion.apply_async(
                kwargs={"build_pk": str(build.pk)}
            )
        )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def wait_for_build_completion(*, build_pk, retries=0):
    Build = apps.get_model(  # noqa: N806
        app_label="codebuild", model_name="Build"
    )

    build = Build.objects.get(pk=build_pk)

    with transaction.atomic():
        build.refresh_status()

        if build.status == build.BuildStatusChoices.IN_PROGRESS:
            _retry(
                task=wait_for_build_completion,
                signature_kwargs={"kwargs": {"build_pk": build_pk}},
                retries=retries,
            )
            return
        else:
            build.refresh_logs()
            build.save()
            if build.status == build.BuildStatusChoices.SUCCEEDED:
                on_commit(
                    lambda: add_image_to_algorithm.apply_async(
                        kwargs={"build_pk": str(build_pk)}
                    )
                )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def add_image_to_algorithm(*, build_pk):
    Build = apps.get_model(  # noqa: N806
        app_label="codebuild", model_name="Build"
    )

    build = Build.objects.get(pk=build_pk)

    if not build.algorithm_image.image:
        build.add_image_to_algorithm()
