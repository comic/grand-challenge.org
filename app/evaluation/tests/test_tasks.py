import os

import docker
import factory
import pytest
from django.conf import settings
from django.db.models import signals

from evaluation.tasks import evaluate_submission
from evaluation.tests.factories import SubmissionFactory, JobFactory, MethodFactory


def create_test_evaluation_container() -> str:
    """
    Creates the example evaluation container
    """
    outfile = '/tmp/test_evaluation.tar'

    client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)

    im = client.images.build(
        path=os.path.join(os.path.split(__file__)[0], 'resources', 'docker'),
        tag='test_evaluation:latest')

    assert im.id in [x.id for x in client.images.list()]

    cli = docker.APIClient(base_url=settings.DOCKER_BASE_URL)
    image = cli.get_image('test_evaluation:latest')

    with open(outfile, 'wb') as f:
        f.write(image.data)

    client.images.remove(image=im.id)

    assert im.id not in [x.id for x in client.images.list()]

    return outfile


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_submission_evaluation():
    # Upload a submission and create a job
    testfile = os.path.join(os.path.split(__file__)[0], 'resources',
                            'compressed.zip')

    submission = SubmissionFactory(file__from_path=testfile)

    eval_container = create_test_evaluation_container()
    method = MethodFactory(container__from_path=eval_container)

    job = JobFactory(submission=submission, method=method)

    res = evaluate_submission(job=job)
    assert res == 'hello world\n'
