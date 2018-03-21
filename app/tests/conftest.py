import os
import zipfile
from collections import namedtuple

import docker
import pytest
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from challenges.models import ComicSite
from tests.factories import UserFactory, ChallengeFactory, MethodFactory

""" Defines fixtures than can be used across all of the tests """


@pytest.fixture(name='ChallengeSet')
def challenge_set():
    """ Creates a challenge with creator, 2 participants, and non participant.
    To use this you must mark the test with @pytest.mark.django_db """
    ChallengeSet = namedtuple(
        'ChallengeSet',
        [
            'challenge',
            'creator',
            'admin',
            'participant',
            'participant1',
            'non_participant',
        ],
    )
    creator = UserFactory()
    challenge = ChallengeFactory(creator=creator)
    admin = UserFactory()
    challenge.add_admin(admin)
    participant = UserFactory()
    challenge.add_participant(participant)
    participant1 = UserFactory()
    challenge.add_participant(participant1)
    non_participant = UserFactory()
    try:
        ComicSite.objects.get(short_name=settings.MAIN_PROJECT_NAME)
    except ObjectDoesNotExist:
        ChallengeFactory(short_name=settings.MAIN_PROJECT_NAME)
    return ChallengeSet(
        challenge, creator, admin, participant, participant1, non_participant
    )


@pytest.fixture(name='TwoChallengeSets')
def two_challenge_sets():
    """ Creates two challenges with combination participants and admins """
    TwoChallengeSets = namedtuple(
        'TwoChallengeSets',
        [
            'ChallengeSet1',
            'ChallengeSet2',
            'admin12',
            'participant12',
            'admin1participant2',
        ],
    )
    ChallengeSet1 = challenge_set()
    ChallengeSet2 = challenge_set()
    admin12 = UserFactory()
    ChallengeSet1.challenge.add_admin(admin12)
    ChallengeSet2.challenge.add_admin(admin12)
    participant12 = UserFactory()
    ChallengeSet1.challenge.add_participant(participant12)
    ChallengeSet2.challenge.add_participant(participant12)
    admin1participant2 = UserFactory()
    ChallengeSet1.challenge.add_admin(admin1participant2)
    ChallengeSet2.challenge.add_participant(admin1participant2)
    return TwoChallengeSets(
        ChallengeSet1,
        ChallengeSet2,
        admin12,
        participant12,
        admin1participant2,
    )


@pytest.fixture(name='EvalChallengeSet')
def challenge_set_with_evaluation(ChallengeSet):
    """ Creates a challenge with two methods.
    To use this you must mark the test with @pytest.mark.django_db """
    EvalChallengeSet = namedtuple(
        'EvalChallengeSet', ['ChallengeSet', 'method']
    )
    ChallengeSet.challenge.use_evaluation = True
    ChallengeSet.challenge.save()
    method = MethodFactory(
        challenge=ChallengeSet.challenge, creator=ChallengeSet.creator
    )
    return EvalChallengeSet(ChallengeSet, method)


@pytest.fixture(scope='session')
def evaluation_image(tmpdir_factory):
    """
    Creates the example evaluation container
    """
    client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)
    im, _ = client.images.build(
        path=os.path.join(
            os.path.split(__file__)[0],
            'evaluation_tests',
            'resources',
            'docker',
        ),
        tag='test_evaluation:latest',
    )
    assert im.id in [x.id for x in client.images.list()]
    cli = docker.APIClient(base_url=settings.DOCKER_BASE_URL)
    image = cli.get_image('test_evaluation:latest')
    outfile = tmpdir_factory.mktemp('docker').join('evaluation-latest.tar')
    with outfile.open(mode='wb') as f:
        for chunk in image:
            f.write(chunk)
    client.images.remove(image=im.id)
    assert im.id not in [x.id for x in client.images.list()]
    return outfile, im.id


@pytest.fixture(scope='session')
def alpine_images(tmpdir_factory):
    client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)
    client.images.pull('alpine:3.6')
    client.images.pull('alpine:3.7')
    cli = docker.APIClient(base_url=settings.DOCKER_BASE_URL)
    # get all images and put them in a tar archive
    image = cli.get_image('alpine')
    outfile = tmpdir_factory.mktemp('alpine').join('alpine.tar')
    with outfile.open('wb') as f:
        for chunk in image:
            f.write(chunk)
    return outfile


@pytest.fixture(scope='session')
def submission_file(tmpdir_factory):
    testfile = tmpdir_factory.mktemp('submission').join('submission.zip')
    z = zipfile.ZipFile(testfile, mode='w')
    try:
        z.write(
            os.path.join(
                os.path.split(__file__)[0],
                'evaluation_tests',
                'resources',
                'submission.csv',
            ),
            compress_type=zipfile.ZIP_DEFLATED,
            arcname='submission.csv',
        )
    finally:
        z.close()
    return testfile
