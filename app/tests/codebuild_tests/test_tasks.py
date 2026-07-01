import pytest

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.codebuild.models import Build, BuildStatusChoices
from grandchallenge.codebuild.tasks import (
    add_image_to_algorithm,
    create_codebuild_build,
    handle_completed_build_event,
)
from grandchallenge.components.models import ImportStatusChoices
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.github_tests.factories import GitHubWebhookMessageFactory


class TestCreateCodebuildBuild:
    @pytest.mark.django_db
    def test_creates_algorithm_image_and_build(
        self, codebuild_stubber, settings
    ):
        client, stubber = codebuild_stubber
        settings.CODEBUILD_PROJECT_NAME = "my-project"

        algorithm = AlgorithmFactory(repo_name="DIAGNijmegen/rse-panimg")
        webhook_message = GitHubWebhookMessageFactory(
            zipfile="github/zips/test.zip"
        )

        stubber.add_response(
            method="start_build",
            service_response={
                "build": {
                    "id": "my-project:build-456",
                    "buildStatus": "IN_PROGRESS",
                }
            },
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            create_codebuild_build(pk=webhook_message.pk)

        build = Build.objects.get(webhook_message=webhook_message)
        assert build.algorithm_image is not None
        assert build.algorithm_image.algorithm == algorithm
        assert build.build_id == "my-project:build-456"
        assert build.status == BuildStatusChoices.IN_PROGRESS

    @pytest.mark.django_db
    def test_skips_if_build_already_exists(self, codebuild_stubber, settings):
        client, stubber = codebuild_stubber
        settings.CODEBUILD_PROJECT_NAME = "my-project"

        AlgorithmFactory(repo_name="DIAGNijmegen/rse-panimg")
        webhook_message = GitHubWebhookMessageFactory(
            zipfile="github/zips/test.zip"
        )

        stubber.add_response(
            method="start_build",
            service_response={
                "build": {
                    "id": "my-project:build-456",
                    "buildStatus": "IN_PROGRESS",
                }
            },
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            create_codebuild_build(pk=webhook_message.pk)
            create_codebuild_build(pk=webhook_message.pk)

        assert (
            Build.objects.filter(webhook_message=webhook_message).count() == 1
        )

    @pytest.mark.django_db
    def test_skips_if_repo_not_linked(self, codebuild_stubber):
        client, stubber = codebuild_stubber
        webhook_message = GitHubWebhookMessageFactory()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            create_codebuild_build(pk=webhook_message.pk)

        assert not Build.objects.exists()

    @pytest.mark.django_db
    def test_algorithm_image_has_no_image_file(
        self, codebuild_stubber, settings
    ):
        client, stubber = codebuild_stubber
        settings.CODEBUILD_PROJECT_NAME = "my-project"

        AlgorithmFactory(repo_name="DIAGNijmegen/rse-panimg")
        webhook_message = GitHubWebhookMessageFactory(
            zipfile="github/zips/test.zip"
        )

        stubber.add_response(
            method="start_build",
            service_response={
                "build": {
                    "id": "my-project:build-789",
                    "buildStatus": "IN_PROGRESS",
                }
            },
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            create_codebuild_build(pk=webhook_message.pk)

        build = Build.objects.get(webhook_message=webhook_message)
        assert not build.algorithm_image.image


class TestHandleCompletedBuildEvent:
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
    def test_cancels_image_on_failure(self, build, build_status, logs_stubber):
        client, stubber = logs_stubber
        stubber.add_response(
            method="get_log_events",
            service_response={
                "events": [],
                "nextForwardToken": "f/0",
                "nextBackwardToken": "b/0",
            },
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            handle_completed_build_event(
                build_arn=f"arn:aws:codebuild:us-east-1:123456789:build/{build.build_id}",
                build_status=build_status,
            )

        build.algorithm_image.refresh_from_db()
        assert (
            build.algorithm_image.import_status
            == ImportStatusChoices.CANCELLED
        )

    @pytest.mark.django_db
    def test_does_not_cancel_image_on_success(
        self, build, logs_stubber, django_capture_on_commit_callbacks
    ):
        client, stubber = logs_stubber
        stubber.add_response(
            method="get_log_events",
            service_response={
                "events": [],
                "nextForwardToken": "f/0",
                "nextBackwardToken": "b/0",
            },
        )

        with (
            pytest.MonkeyPatch.context() as mp,
            django_capture_on_commit_callbacks(),
        ):
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            handle_completed_build_event(
                build_arn=f"arn:aws:codebuild:us-east-1:123456789:build/{build.build_id}",
                build_status=BuildStatusChoices.SUCCEEDED,
            )

        build.algorithm_image.refresh_from_db()
        assert (
            build.algorithm_image.import_status
            == ImportStatusChoices.INITIALIZED
        )

    @pytest.mark.django_db
    def test_updates_build_status(self, build, logs_stubber):
        client, stubber = logs_stubber
        stubber.add_response(
            method="get_log_events",
            service_response={
                "events": [],
                "nextForwardToken": "f/0",
                "nextBackwardToken": "b/0",
            },
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            handle_completed_build_event(
                build_arn=f"arn:aws:codebuild:us-east-1:123456789:build/{build.build_id}",
                build_status=BuildStatusChoices.FAILED,
            )

        build.refresh_from_db()
        assert build.status == BuildStatusChoices.FAILED

    @pytest.mark.django_db
    def test_stores_build_log(self, build, logs_stubber):
        client, stubber = logs_stubber
        stubber.add_response(
            method="get_log_events",
            service_response={
                "events": [
                    {"message": "[Container] skipped\n"},
                    {"message": "Step 1: Building image\n"},
                    {"message": "Step 2: Pushing image\n"},
                ],
                "nextForwardToken": "f/0",
                "nextBackwardToken": "b/0",
            },
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            handle_completed_build_event(
                build_arn=f"arn:aws:codebuild:us-east-1:123456789:build/{build.build_id}",
                build_status=BuildStatusChoices.FAILED,
            )

        build.refresh_from_db()
        assert (
            build.build_log
            == "Step 1: Building image\nStep 2: Pushing image\n"
        )

    @pytest.mark.django_db
    def test_is_idempotent(self, build, logs_stubber):
        client, stubber = logs_stubber
        stubber.add_response(
            method="get_log_events",
            service_response={
                "events": [],
                "nextForwardToken": "f/0",
                "nextBackwardToken": "b/0",
            },
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("boto3.client", lambda *args, **kwargs: client)
            handle_completed_build_event(
                build_arn=f"arn:aws:codebuild:us-east-1:123456789:build/{build.build_id}",
                build_status=BuildStatusChoices.FAILED,
            )

            # Calling again is a no-op since status is no longer IN_PROGRESS
            handle_completed_build_event(
                build_arn=f"arn:aws:codebuild:us-east-1:123456789:build/{build.build_id}",
                build_status=BuildStatusChoices.SUCCEEDED,
            )

        build.refresh_from_db()
        assert build.status == BuildStatusChoices.FAILED


class TestAddImageToAlgorithm:
    @pytest.mark.django_db
    def test_copies_image_and_deletes_artifacts(
        self, build, s3_stubber, monkeypatch
    ):
        client, stubber = s3_stubber

        copy_called = False

        def fake_copy_s3_object(**kwargs):
            nonlocal copy_called
            copy_called = True

        monkeypatch.setattr(
            "grandchallenge.codebuild.models.copy_s3_object",
            fake_copy_s3_object,
        )

        stubber.add_response(
            method="list_objects_v2",
            service_response={
                "IsTruncated": False,
                "Contents": [
                    {
                        "Key": "codebuild/artifacts/build-123/test-project/container-image.tar.gz"
                    }
                ],
            },
        )
        stubber.add_response(
            method="delete_objects",
            service_response={
                "Deleted": [
                    {
                        "Key": "codebuild/artifacts/build-123/test-project/container-image.tar.gz"
                    }
                ]
            },
        )

        monkeypatch.setattr("boto3.client", lambda *args, **kwargs: client)
        add_image_to_algorithm(build_pk=build.pk)

        assert copy_called

    @pytest.mark.django_db
    def test_skips_copy_if_image_already_set(
        self, build, s3_stubber, monkeypatch
    ):
        # Set image directly via queryset to avoid triggering validation
        AlgorithmImage.objects.filter(pk=build.algorithm_image.pk).update(
            image="some/path.tar.gz"
        )

        copy_called = False

        def fake_copy_s3_object(**kwargs):
            nonlocal copy_called
            copy_called = True

        monkeypatch.setattr(
            "grandchallenge.codebuild.models.copy_s3_object",
            fake_copy_s3_object,
        )

        client, stubber = s3_stubber
        stubber.add_response(
            method="list_objects_v2",
            service_response={"IsTruncated": False},
        )

        monkeypatch.setattr("boto3.client", lambda *args, **kwargs: client)
        add_image_to_algorithm(build_pk=build.pk)

        assert not copy_called
