import os
import zipfile
from collections import namedtuple
from pathlib import Path
from subprocess import call
from typing import NamedTuple

import docker
import pytest
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group

from grandchallenge.challenges.models import Challenge
from tests.factories import (
    UserFactory,
    ChallengeFactory,
    MethodFactory,
    ImageFactory,
)
from tests.annotations_tests.factories import (
    MeasurementAnnotationFactory,
    BooleanClassificationAnnotationFactory,
    IntegerClassificationAnnotationFactory,
    PolygonAnnotationSetFactory,
    CoordinateListAnnotationFactory,
    LandmarkAnnotationSetFactory,
    ETDRSGridAnnotationFactory,
    SingleLandmarkAnnotationFactory,
    SinglePolygonAnnotationFactory,
)

""" Defines fixtures than can be used across all of the tests """


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """ Ensure that the main challenge has been created """
    with django_db_blocker.unblock():
        # Set the default domain that is used in RequestFactory
        site = Site.objects.get(pk=settings.SITE_ID)
        site.domain = "testserver"
        site.save()

        # The main project should always exist
        Challenge.objects.create(short_name=settings.MAIN_PROJECT_NAME)


class ChallengeSet(NamedTuple):
    challenge: ChallengeFactory
    creator: UserFactory
    admin: UserFactory
    participant: UserFactory
    participant1: UserFactory
    non_participant: UserFactory


def generate_challenge_set():
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
        Challenge.objects.get(short_name=settings.MAIN_PROJECT_NAME)
    except ObjectDoesNotExist:
        ChallengeFactory(short_name=settings.MAIN_PROJECT_NAME)

    return ChallengeSet(
        challenge=challenge,
        creator=creator,
        admin=admin,
        participant=participant,
        participant1=participant1,
        non_participant=non_participant,
    )


@pytest.fixture(name="ChallengeSet")
def challenge_set():
    """ Creates a challenge with creator, 2 participants, and non participant.
    To use this you must mark the test with @pytest.mark.django_db """
    return generate_challenge_set()


@pytest.fixture(name="TwoChallengeSets")
def two_challenge_sets():
    """ Creates two challenges with combination participants and admins """
    TwoChallengeSets = namedtuple(
        "TwoChallengeSets",
        [
            "ChallengeSet1",
            "ChallengeSet2",
            "admin12",
            "participant12",
            "admin1participant2",
        ],
    )
    ChallengeSet1 = generate_challenge_set()
    ChallengeSet2 = generate_challenge_set()
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


@pytest.fixture(name="EvalChallengeSet")
def challenge_set_with_evaluation(ChallengeSet):
    """ Creates a challenge with two methods.
    To use this you must mark the test with @pytest.mark.django_db """
    EvalChallengeSet = namedtuple(
        "EvalChallengeSet", ["ChallengeSet", "method"]
    )
    ChallengeSet.challenge.use_evaluation = True
    ChallengeSet.challenge.save()
    method = MethodFactory(
        challenge=ChallengeSet.challenge, creator=ChallengeSet.creator
    )
    return EvalChallengeSet(ChallengeSet, method)


@pytest.fixture(scope="session")
def evaluation_image(tmpdir_factory):
    """
    Creates the example evaluation container
    """
    client = docker.DockerClient(
        base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL
    )
    im, _ = client.images.build(
        path=os.path.join(
            os.path.split(__file__)[0],
            "evaluation_tests",
            "resources",
            "docker",
        ),
        tag="test_evaluation:latest",
    )
    assert im.id in [x.id for x in client.images.list()]
    cli = docker.APIClient(base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL)
    image = cli.get_image("test_evaluation:latest")
    outfile = tmpdir_factory.mktemp("docker").join("evaluation-latest.tar")
    with outfile.open(mode="wb") as f:
        for chunk in image:
            f.write(chunk)
    client.images.remove(image=im.id)

    call(["gzip", outfile])

    assert im.id not in [x.id for x in client.images.list()]
    return f"{outfile}.gz", im.id


@pytest.fixture(scope="session")
def alpine_images(tmpdir_factory):
    client = docker.DockerClient(
        base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL
    )
    client.images.pull("alpine:3.7")
    client.images.pull("alpine:3.8")
    cli = docker.APIClient(base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL)
    # get all images and put them in a tar archive
    image = cli.get_image("alpine")
    outfile = tmpdir_factory.mktemp("alpine").join("alpine.tar")
    with outfile.open("wb") as f:
        for chunk in image:
            f.write(chunk)
    return outfile


@pytest.fixture(scope="session")
def root_image(tmpdir_factory):
    client = docker.DockerClient(
        base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL
    )
    client.images.pull("alpine:3.8")

    cli = docker.APIClient(base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL)
    image = cli.get_image("alpine:3.8")
    outfile = tmpdir_factory.mktemp("alpine").join("alpine.tar")

    with outfile.open("wb") as f:
        for chunk in image:
            f.write(chunk)

    return outfile


@pytest.fixture(scope="session")
def submission_file(tmpdir_factory):
    testfile = tmpdir_factory.mktemp("submission").join("submission.zip")
    z = zipfile.ZipFile(testfile, mode="w")

    files = [
        Path("evaluation_tests") / "resources" / "submission.csv",
        Path("cases_tests") / "resources" / "image10x10x10.mhd",
        Path("cases_tests") / "resources" / "image10x10x10.zraw",
    ]

    try:
        for file in files:
            if "cases_tests" in str(file.parent):
                arcname = Path("submission") / Path("images") / file.name
            else:
                arcname = Path("submission") / file.name

            z.write(
                Path(__file__).parent / file,
                compress_type=zipfile.ZIP_DEFLATED,
                arcname=arcname,
            )
    finally:
        z.close()

    return testfile


class AnnotationSet(NamedTuple):
    grader: UserFactory
    measurement: MeasurementAnnotationFactory
    boolean: BooleanClassificationAnnotationFactory
    integer: IntegerClassificationAnnotationFactory
    polygon: PolygonAnnotationSetFactory
    coordinatelist: CoordinateListAnnotationFactory
    landmark: LandmarkAnnotationSetFactory
    etdrs: ETDRSGridAnnotationFactory


def generate_annotation_set(retina_grader=False):
    grader = UserFactory()

    if retina_grader:
        # Add to retina_graders group
        grader.groups.add(
            Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
        )

    measurement = MeasurementAnnotationFactory(grader=grader)
    boolean = BooleanClassificationAnnotationFactory(grader=grader)
    integer = IntegerClassificationAnnotationFactory(grader=grader)
    polygon = PolygonAnnotationSetFactory(grader=grader)
    coordinatelist = CoordinateListAnnotationFactory(grader=grader)
    landmark = LandmarkAnnotationSetFactory(grader=grader)
    etdrs = ETDRSGridAnnotationFactory(grader=grader)

    # Create child models for polygon annotation set
    SinglePolygonAnnotationFactory.create_batch(10, annotation_set=polygon)

    # Create child models for landmark annotation set (3 per image)
    for i in range(5):
        image = ImageFactory()
        SingleLandmarkAnnotationFactory(annotation_set=landmark, image=image)

    return AnnotationSet(
        grader=grader,
        measurement=measurement,
        boolean=boolean,
        polygon=polygon,
        coordinatelist=coordinatelist,
        landmark=landmark,
        etdrs=etdrs,
        integer=integer,
    )


@pytest.fixture(name="AnnotationSet")
def annotation_set():
    """ Creates a user with the one of each of the following annotations: Measurement,
    BooleanClassification, PolygonAnnotationSet (with 10 child annotations), CoordinateList,
    LandmarkAnnotationSet(with single landmark annotations for 5 images), ETDRSGrid """
    return generate_annotation_set()


class TwoPolygonAnnotationSets(NamedTuple):
    grader1: UserFactory
    grader2: UserFactory
    polygonset1: PolygonAnnotationSetFactory
    polygonset2: PolygonAnnotationSetFactory


def generate_two_polygon_annotation_sets(retina_grader=False):
    graders = (UserFactory(), UserFactory())

    if retina_grader:
        # Add to retina_graders group
        for grader in graders:
            grader.groups.add(
                Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
            )

    polygonsets = (
        PolygonAnnotationSetFactory(grader=graders[0]),
        PolygonAnnotationSetFactory(grader=graders[1]),
    )

    # Create child models for polygon annotation set
    singlepolygonbatches = (
        SinglePolygonAnnotationFactory.create_batch(
            10, annotation_set=polygonsets[0]
        ),
        SinglePolygonAnnotationFactory.create_batch(
            10, annotation_set=polygonsets[1]
        ),
    )

    return TwoPolygonAnnotationSets(
        grader1=graders[0],
        grader2=graders[1],
        polygonset1=polygonsets[0],
        polygonset2=polygonsets[1],
    )


@pytest.fixture(name="TwoRetinaPolygonAnnotationSets")
def two_retina_polygon_annotation_sets():
    """ Creates two PolygonAnnotationSets with each 10 SinglePolygonAnnotations belonging to
    two different graders that both are in the retina_graders group """
    return generate_two_polygon_annotation_sets(retina_grader=True)


@pytest.fixture(name="TwoPolygonAnnotationSets")
def two_polygon_annotation_sets():
    """ Creates two PolygonAnnotationSets with each 10 SinglePolygonAnnotations belonging to
    two different graders """
    return generate_two_polygon_annotation_sets(retina_grader=False)
