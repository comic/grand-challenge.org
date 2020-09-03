from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase

from grandchallenge.components.tasks import validate_docker_image
from grandchallenge.evaluation.models import AlgorithmEvaluation, Method
from grandchallenge.evaluation.tasks import set_evaluation_inputs
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.evaluation_tests.factories import (
    AlgorithmEvaluationFactory,
    EvaluationFactory,
    MethodFactory,
    SubmissionFactory,
)


@pytest.mark.django_db
def test_submission_evaluation(
    client, evaluation_image, submission_file, settings
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # Upload a submission and create an evaluation
    eval_container, sha256 = evaluation_image
    method = MethodFactory(
        image__from_path=eval_container, image_sha256=sha256, ready=True
    )

    # We should not be able to download methods
    with pytest.raises(NotImplementedError):
        _ = method.image.url

    # This will create an evaluation, and we'll wait for it to be executed
    submission = SubmissionFactory(
        predictions_file__from_path=submission_file, phase=method.phase
    )

    # The evaluation method should return the correct answer
    assert len(submission.evaluation_set.all()) == 1
    assert (
        submission.evaluation_set.first()
        .outputs.get(interface__slug="metrics-json-file")
        .value["acc"]
        == 0.5
    )

    # Try with a csv file
    submission = SubmissionFactory(
        predictions_file__from_path=Path(__file__).parent
        / "resources"
        / "submission.csv",
        phase=method.phase,
    )

    assert len(submission.evaluation_set.all()) == 1
    assert (
        submission.evaluation_set.first()
        .outputs.get(interface__slug="metrics-json-file")
        .value["acc"]
        == 0.5
    )


@pytest.mark.django_db
def test_method_validation(evaluation_image):
    """The validator should set the correct sha256 and set the ready bit."""
    container, sha256 = evaluation_image
    method = MethodFactory(image__from_path=container)

    # The method factory fakes the sha256 on creation
    assert method.image_sha256 != sha256
    assert method.ready is False

    validate_docker_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.image_sha256 == sha256
    assert method.ready is True


@pytest.mark.django_db
def test_method_validation_invalid_dockerfile(alpine_images):
    """Uploading two images in a tar archive should fail."""
    method = MethodFactory(image__from_path=alpine_images)
    assert method.ready is False

    with pytest.raises(ValidationError):
        validate_docker_image(
            pk=method.pk,
            app_label=method._meta.app_label,
            model_name=method._meta.model_name,
        )

    method = Method.objects.get(pk=method.pk)
    assert method.ready is False
    assert "should only have 1 image" in method.status


@pytest.mark.django_db
def test_method_validation_root_dockerfile(root_image):
    """Uploading two images in a tar archive should fail."""
    method = MethodFactory(image__from_path=root_image)
    assert method.ready is False

    with pytest.raises(ValidationError):
        validate_docker_image(
            pk=method.pk,
            app_label=method._meta.app_label,
            model_name=method._meta.model_name,
        )

    method = Method.objects.get(pk=method.pk)
    assert method.ready is False
    assert "runs as root" in method.status


@pytest.mark.django_db
def test_method_validation_not_a_docker_tar(submission_file):
    """Upload something that isn't a docker file should be invalid."""
    method = MethodFactory(image__from_path=submission_file)
    assert method.ready is False

    with pytest.raises(ValidationError):
        validate_docker_image(
            pk=method.pk,
            app_label=method._meta.app_label,
            model_name=method._meta.model_name,
        )

    method = Method.objects.get(pk=method.pk)
    assert method.ready is False
    assert "manifest.json not found" in method.status


class TestSetEvaluationInputs(TestCase):
    def test_unsuccessful_jobs_fail_evaluation(self):
        submission = SubmissionFactory()
        evaluation = EvaluationFactory(submission=submission)
        AlgorithmEvaluationFactory(
            status=AlgorithmEvaluation.SUCCESS, submission=submission
        )
        AlgorithmEvaluationFactory(
            status=AlgorithmEvaluation.FAILURE, submission=submission
        )

        set_evaluation_inputs(evaluation_pk=evaluation.pk)

        evaluation.refresh_from_db()
        assert evaluation.status == evaluation.FAILURE
        assert (
            evaluation.output == "The algorithm failed to execute on 1 images."
        )

    def test_set_evaluation_inputs(self):
        submission = SubmissionFactory()
        evaluation = EvaluationFactory(submission=submission)
        algorithms = AlgorithmEvaluationFactory.create_batch(
            2, status=AlgorithmEvaluation.SUCCESS, submission=submission
        )
        civs = ComponentInterfaceValueFactory.create_batch(2)

        for alg, civ in zip(algorithms, civs):
            alg.outputs.set([civ])

        set_evaluation_inputs(evaluation_pk=evaluation.pk)

        evaluation.refresh_from_db()
        assert evaluation.status == evaluation.PENDING
        assert evaluation.output == ""
        assert evaluation.inputs.count() == 1
