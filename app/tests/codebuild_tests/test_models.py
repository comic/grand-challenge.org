import pytest

from grandchallenge.codebuild.models import Build, BuildStatusChoices
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.github_tests.factories import GitHubWebhookMessageFactory


@pytest.mark.django_db
def test_build_number(build):
    assert build.build_number == "build-123"


@pytest.mark.django_db
def test_animate_when_in_progress(build):
    assert build.animate is True


@pytest.mark.django_db
def test_not_animate_when_finished(build):
    build.status = BuildStatusChoices.SUCCEEDED
    assert build.animate is False


@pytest.mark.django_db
def test_finished_when_not_in_progress(build):
    build.status = BuildStatusChoices.FAILED
    assert build.finished is True


@pytest.mark.django_db
def test_not_finished_when_in_progress(build):
    assert build.finished is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status,expected_context",
    [
        (BuildStatusChoices.SUCCEEDED, "success"),
        (BuildStatusChoices.STOPPED, "warning"),
        (BuildStatusChoices.FAILED, "danger"),
        (BuildStatusChoices.FAULT, "danger"),
        (BuildStatusChoices.TIMED_OUT, "danger"),
        (BuildStatusChoices.IN_PROGRESS, "info"),
    ],
)
def test_status_context(build, status, expected_context):
    build.status = status
    assert build.status_context == expected_context


@pytest.mark.django_db
def test_save_calls_start_build(codebuild_stubber, settings):
    client, stubber = codebuild_stubber
    settings.CODEBUILD_PROJECT_NAME = "my-project"

    algorithm_image = AlgorithmImageFactory(image=None)
    webhook_message = GitHubWebhookMessageFactory(
        zipfile="github/zips/test.zip"
    )

    stubber.add_response(
        method="start_build",
        service_response={
            "build": {
                "id": "my-project:build-999",
                "buildStatus": "IN_PROGRESS",
            }
        },
    )

    build = Build(
        webhook_message=webhook_message,
        algorithm_image=algorithm_image,
    )
    build._Build__codebuild_client = client
    build.save()

    assert build.build_id == "my-project:build-999"
    assert build.status == BuildStatusChoices.IN_PROGRESS
