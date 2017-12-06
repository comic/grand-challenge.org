import os
import tempfile
import zipfile
from typing import Tuple

import docker
import factory
import pytest
from django.conf import settings
from django.db.models import signals

from evaluation.tasks import evaluate_submission
from tests.factories import SubmissionFactory, JobFactory, \
    MethodFactory, UserFactory


def create_test_evaluation_container(client) -> Tuple[str,str]:
    """
    Creates the example evaluation container
    """

    im = client.images.build(
        path=os.path.join(os.path.split(__file__)[0], 'resources', 'docker'),
        tag='test_evaluation:latest')

    assert im.id in [x.id for x in client.images.list()]

    cli = docker.APIClient(base_url=settings.DOCKER_BASE_URL)
    image = cli.get_image('test_evaluation:latest')

    with tempfile.NamedTemporaryFile(suffix='.tar', mode='wb',
                                     delete=False) as f:
        f.write(image.data)
        outfile = f.name

    client.images.remove(image=im.id)

    assert im.id not in [x.id for x in client.images.list()]

    return (outfile, im.id)


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_submission_evaluation(client):
    # Upload a submission and create a job

    dockerclient = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)

    with tempfile.NamedTemporaryFile(mode='r', suffix='.zip',
                                     delete=False) as f:
        testfile = f.name

    z = zipfile.ZipFile(testfile, mode='w')
    try:
        z.write(os.path.join(os.path.split(__file__)[0], 'resources',
                             'submission.csv'),
                compress_type=zipfile.ZIP_DEFLATED,
                arcname='submission.csv')
    finally:
        z.close()

    user = UserFactory()

    submission = SubmissionFactory(file__from_path=testfile, creator=user)

    eval_container, sha256 = create_test_evaluation_container(dockerclient)
    method = MethodFactory(image__from_path=eval_container,
                           image_sha256=sha256,
                           ready=True)

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
