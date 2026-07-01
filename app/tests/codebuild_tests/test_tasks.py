import pytest

from grandchallenge.codebuild.models import Build, BuildStatusChoices
from grandchallenge.components.models import ImportStatusChoices
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.github_tests.factories import GitHubWebhookMessageFactory


@pytest.fixture
def build(mocker):
    algorithm_image = AlgorithmImageFactory(image=None)
    webhook_message = GitHubWebhookMessageFactory()
    mocker.patch.object(Build, "_create_build")
    build = Build.objects.create(
        webhook_message=webhook_message,
        algorithm_image=algorithm_image,
        build_config={"projectName": "test-project"},
        build_id="project:build-123",
        status=BuildStatusChoices.IN_PROGRESS,
    )
    return build


@pytest.mark.django_db
@pytest.mark.parametrize(
    "build_status",
    [
        BuildStatusChoices.FAILED,
        BuildStatusChoices.FAULT,
        BuildStatusChoices.TIMED_OUT,
        BuildStatusChoices.STOPPED,
    ],
)
def test_handle_completed_build_event_cancels_image_on_failure(
    build, build_status, mocker
):
    from grandchallenge.codebuild.tasks import handle_completed_build_event

    mocker.patch.object(Build, "refresh_logs")

    handle_completed_build_event(
        build_arn=f"arn:aws:codebuild:us-east-1:123456789:build/{build.build_id}",
        build_status=build_status,
    )

    build.algorithm_image.refresh_from_db()
    assert build.algorithm_image.import_status == ImportStatusChoices.CANCELLED


@pytest.mark.django_db
def test_handle_completed_build_event_does_not_cancel_image_on_success(
    build, mocker, django_capture_on_commit_callbacks
):
    from grandchallenge.codebuild.tasks import handle_completed_build_event

    mocker.patch.object(Build, "refresh_logs")

    with django_capture_on_commit_callbacks():
        handle_completed_build_event(
            build_arn=f"arn:aws:codebuild:us-east-1:123456789:build/{build.build_id}",
            build_status=BuildStatusChoices.SUCCEEDED,
        )

    build.algorithm_image.refresh_from_db()
    assert (
        build.algorithm_image.import_status == ImportStatusChoices.INITIALIZED
    )
