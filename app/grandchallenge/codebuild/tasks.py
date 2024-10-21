from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.transaction import on_commit

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage
from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)


@acks_late_micro_short_task
@transaction.atomic
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

    algorithm_image = AlgorithmImage.objects.create(algorithm=algorithm)

    Build.objects.create(webhook_message=ghwm, algorithm_image=algorithm_image)


@acks_late_micro_short_task
@transaction.atomic
def handle_completed_build_event(*, build_arn, build_status):
    build_id = build_arn.split("/")[-1]

    Build = apps.get_model(  # noqa: N806
        app_label="codebuild", model_name="Build"
    )

    build = Build.objects.get(build_id=build_id)

    if build.status != build.BuildStatusChoices.IN_PROGRESS:
        return

    build.status = build_status
    build.refresh_logs()

    build.full_clean()
    build.save()

    if build.status == build.BuildStatusChoices.SUCCEEDED:
        on_commit(
            lambda: add_image_to_algorithm.apply_async(
                kwargs={"build_pk": str(build.pk)}
            )
        )


@acks_late_2xlarge_task
def add_image_to_algorithm(*, build_pk):
    Build = apps.get_model(  # noqa: N806
        app_label="codebuild", model_name="Build"
    )

    build = Build.objects.get(pk=build_pk)

    if not build.algorithm_image.image:
        build.add_image_to_algorithm()

    build.delete_artifacts()
