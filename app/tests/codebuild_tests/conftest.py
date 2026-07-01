import boto3
import pytest
from botocore.stub import Stubber

from grandchallenge.codebuild.models import Build
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.github_tests.factories import GitHubWebhookMessageFactory


@pytest.fixture
def codebuild_stubber():
    client = boto3.client("codebuild", region_name="us-east-1")
    with Stubber(client) as stubber:
        yield client, stubber


@pytest.fixture
def logs_stubber():
    client = boto3.client("logs", region_name="us-east-1")
    with Stubber(client) as stubber:
        yield client, stubber


@pytest.fixture
def s3_stubber():
    client = boto3.client("s3", region_name="us-east-1")
    with Stubber(client) as stubber:
        yield client, stubber


@pytest.fixture
def build(codebuild_stubber, settings):
    client, stubber = codebuild_stubber
    settings.CODEBUILD_PROJECT_NAME = "test-project"
    settings.CODEBUILD_BUILD_LOGS_GROUP_NAME = "test-log-group"
    settings.CODEBUILD_ARTIFACTS_BUCKET_NAME = "test-artifacts-bucket"

    algorithm_image = AlgorithmImageFactory(image=None)
    webhook_message = GitHubWebhookMessageFactory(
        zipfile="github/zips/test.zip"
    )

    stubber.add_response(
        method="start_build",
        service_response={
            "build": {
                "id": "test-project:build-123",
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

    return build
