from pathlib import Path

import docker
import pytest
from django.conf import settings

from grandchallenge.evaluation.models import Method
from grandchallenge.evaluation.tasks import (
    evaluate_submission, validate_method_async
)
from tests.factories import (
    SubmissionFactory, JobFactory, MethodFactory, UserFactory
)


@pytest.mark.django_db
def test_submission_evaluation(client, evaluation_image, submission_file):
    # Upload a submission and create a job

    dockerclient = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)

    user = UserFactory()

    submission = SubmissionFactory(
        file__from_path=submission_file, creator=user
    )

    eval_container, sha256 = evaluation_image

    method = MethodFactory(
        image__from_path=eval_container, image_sha256=sha256, ready=True
    )

    # We should not be able to download methods
    response = client.get(method.image.url)
    assert response.status_code == 403

    job = JobFactory(submission=submission, method=method)

    num_containers_before = len(dockerclient.containers.list())
    num_volumes_before = len(dockerclient.volumes.list())

    res = evaluate_submission(job=job)

    # The evaluation method should return the correct answer
    assert res["acc"] == 0.5
    # The evaluation method should clean up after itself
    assert len(dockerclient.volumes.list()) == num_volumes_before
    assert len(dockerclient.containers.list()) == num_containers_before

    # Try with a csv file
    submission = SubmissionFactory(
        file__from_path=Path(__file__).parent / 'resources' / 'submission.csv',
        creator=user,
    )

    job = JobFactory(submission=submission, method=method)
    res = evaluate_submission(job=job)
    assert res["acc"] == 0.5


@pytest.mark.django_db
def test_method_validation(evaluation_image):
    """ The validator should set the correct sha256 and set the ready bit """
    container, sha256 = evaluation_image
    method = MethodFactory(image__from_path=container)
    # The method factory fakes the sha256 on creation
    assert method.image_sha256 != sha256
    assert method.ready == False
    validate_method_async(method_pk=method.pk)
    method = Method.objects.get(pk=method.pk)
    assert method.image_sha256 == sha256
    assert method.ready == True


@pytest.mark.django_db
def test_method_validation_invalid_dockefile(alpine_images):
    """ Uploading two images in a tar archive should fail """
    method = MethodFactory(image__from_path=alpine_images)
    assert method.ready == False
    validate_method_async(method_pk=method.pk)
    method = Method.objects.get(pk=method.pk)
    assert method.ready == False
    assert 'should only have 1 image' in method.status


@pytest.mark.django_db
def test_method_validation_not_a_docker_tar(submission_file):
    """ Upload something that isnt a docker file should be invalid """
    method = MethodFactory(image__from_path=submission_file)
    assert method.ready == False
    validate_method_async(method_pk=method.pk)
    method = Method.objects.get(pk=method.pk)
    assert method.ready == False
    assert 'manifest.json not found' in method.status
