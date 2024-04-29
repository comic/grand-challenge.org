import os
import warnings
import zipfile
from collections import namedtuple
from pathlib import Path
from typing import NamedTuple

import pytest
from allauth.mfa import recovery_codes, totp
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site

from grandchallenge.components.backends import docker_client
from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.reader_studies.models import Question
from grandchallenge.subdomains.utils import reverse_lazy
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import MethodFactory, PhaseFactory
from tests.factories import (
    SUPER_SECURE_TEST_PASSWORD,
    ChallengeFactory,
    ImageFactory,
    UserFactory,
)
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.workstations_tests.fixtures import (
    TwoWorkstationSets,
    workstation_set,
)


@pytest.fixture
def two_workstation_sets() -> TwoWorkstationSets:
    return TwoWorkstationSets(ws1=workstation_set(), ws2=workstation_set())


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Ensure that the main challenge has been created."""
    with django_db_blocker.unblock():
        # Set the default domain that is used in RequestFactory
        site = Site.objects.get(pk=settings.SITE_ID)
        site.domain = "testserver"
        site.save()


def pytest_itemcollected(item):
    if item.get_closest_marker("playwright") is not None:
        # See https://github.com/microsoft/playwright-pytest/issues/29
        warnings.warn(  # noqa: B028
            "Setting DJANGO_ALLOW_ASYNC_UNSAFE for playwright support"
        )
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


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

    PhaseFactory(challenge=challenge)

    return ChallengeSet(
        challenge=challenge,
        creator=creator,
        admin=admin,
        participant=participant,
        participant1=participant1,
        non_participant=non_participant,
    )


@pytest.fixture(name="challenge_set")
def challenge_set():
    """
    Create a challenge with creator, 2 participants, and non participant.

    To use this you must mark the test with `@pytest.mark.django_db`.
    """
    return generate_challenge_set()


@pytest.fixture(name="two_challenge_sets")
def two_challenge_sets():
    """Creates two challenges with combination participants and admins."""
    two_challenge_sets = namedtuple(
        "two_challenge_sets",
        [
            "challenge_set_1",
            "challenge_set_2",
            "admin12",
            "participant12",
            "admin1participant2",
        ],
    )
    challenge_set_1 = generate_challenge_set()
    challenge_set_2 = generate_challenge_set()
    admin12 = UserFactory()
    challenge_set_1.challenge.add_admin(admin12)
    challenge_set_2.challenge.add_admin(admin12)
    participant12 = UserFactory()
    challenge_set_1.challenge.add_participant(participant12)
    challenge_set_2.challenge.add_participant(participant12)
    admin1participant2 = UserFactory()
    challenge_set_1.challenge.add_admin(admin1participant2)
    challenge_set_2.challenge.add_participant(admin1participant2)

    return two_challenge_sets(
        challenge_set_1,
        challenge_set_2,
        admin12,
        participant12,
        admin1participant2,
    )


@pytest.fixture(name="eval_challenge_set")
def challenge_set_with_evaluation(challenge_set):
    """
    Creates a challenge with two methods.

    To use this you must mark the test with `@pytest.mark.django_db`.
    """
    eval_challenge_set = namedtuple(
        "eval_challenge_set", ["challenge_set", "method"]
    )

    phase = challenge_set.challenge.phase_set.get()

    method = MethodFactory(phase=phase, creator=challenge_set.creator)

    return eval_challenge_set(challenge_set, method)


def docker_image(tmpdir_factory, path, label, full_path=None):
    """Create the docker container."""
    repo_tag = f"test-{label}:latest"

    if not full_path:
        full_path = os.path.join(
            os.path.split(__file__)[0], path, "resources", "docker"
        )

    docker_client.build_image(path=full_path, repo_tag=repo_tag)

    outfile = tmpdir_factory.mktemp("docker").join(f"{label}-latest.tar")
    docker_client.save_image(repo_tag=repo_tag, output=outfile)

    return outfile


@pytest.fixture(scope="session")
def evaluation_image(tmpdir_factory):
    """Create the example evaluation container."""
    container = docker_image(
        tmpdir_factory, path="evaluation_tests", label="evaluation"
    )

    image = docker_client.inspect_image(repo_tag="test-evaluation:latest")
    sha256 = image["Id"]

    return container, sha256


@pytest.fixture(scope="session")
def algorithm_image(tmpdir_factory):
    """Create the example algorithm container."""
    return docker_image(
        tmpdir_factory, path="algorithms_tests", label="algorithm"
    )


@pytest.fixture(scope="session")
def algorithm_io_image(tmpdir_factory):
    """Create the example algorithm container."""
    return docker_image(
        tmpdir_factory,
        path="",
        label="algorithm-io",
        full_path=os.path.join(
            os.path.split(__file__)[0], "resources", "gc_demo_algorithm"
        ),
    )


@pytest.fixture(scope="session")
def alpine_images(tmpdir_factory):
    docker_client.pull_image(repo_tag="alpine:3.16")
    docker_client.pull_image(repo_tag="alpine:3.15")

    # get all images and put them in a tar archive
    outfile = tmpdir_factory.mktemp("alpine").join("alpine_multi.tar")
    docker_client.save_image(repo_tag="alpine", output=outfile)

    return outfile


@pytest.fixture(scope="session")
def root_image(tmpdir_factory):
    docker_client.pull_image(repo_tag="alpine:3.16")

    outfile = tmpdir_factory.mktemp("alpine").join("alpine.tar")
    docker_client.save_image(repo_tag="alpine:3.16", output=outfile)

    return outfile


@pytest.fixture(scope="session")
def http_image(tmpdir_factory):
    return docker_image(
        tmpdir_factory, path="workstations_tests", label="workstation"
    )


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


@pytest.fixture
def reader_study_with_gt():
    rs = ReaderStudyFactory()
    im1, im2 = ImageFactory(name="im1"), ImageFactory(name="im2")
    q1, q2, q3 = [
        QuestionFactory(
            reader_study=rs,
            answer_type=Question.AnswerType.BOOL,
            question_text="q1",
        ),
        QuestionFactory(
            reader_study=rs,
            answer_type=Question.AnswerType.BOOL,
            question_text="q2",
        ),
        QuestionFactory(
            reader_study=rs,
            answer_type=Question.AnswerType.BOOL,
            question_text="q3",
        ),
    ]

    r1, r2, editor = UserFactory(), UserFactory(), UserFactory()
    rs.add_reader(r1)
    rs.add_reader(r2)
    rs.add_editor(editor)
    ci = ComponentInterface.objects.first()
    for im in [im1, im2]:
        civ = ComponentInterfaceValueFactory(image=im)
        ds = DisplaySetFactory(reader_study=rs)
        ds.values.add(civ)
    rs.view_content = {"main": [ci.slug]}
    rs.save()

    for question in [q1, q2, q3]:
        for ds in rs.display_sets.all():
            AnswerFactory(
                question=question,
                creator=editor,
                answer=True,
                is_ground_truth=True,
                display_set=ds,
            )

    return rs


@pytest.fixture
def reader_study_with_mc_gt(reader_study_with_gt):
    rs = reader_study_with_gt

    q_choice = QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.CHOICE,
        question_text="C",
    )
    q_multiple_choice = QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.MULTIPLE_CHOICE,
        question_text="MC",
    )

    c_options = [
        CategoricalOptionFactory(question=q_choice, title="fee"),
        CategoricalOptionFactory(question=q_choice, title="foh"),
        CategoricalOptionFactory(question=q_choice, title="fum"),
    ]

    mc_options = [
        CategoricalOptionFactory(question=q_multiple_choice, title="fee"),
        CategoricalOptionFactory(question=q_multiple_choice, title="foh"),
        CategoricalOptionFactory(question=q_multiple_choice, title="fum"),
    ]

    editor = rs.editors_group.user_set.first()
    for question, answer in [
        (q_choice, c_options[0].id),
        (q_multiple_choice, [mc_options[0].id, mc_options[1].id]),
    ]:
        for ds in rs.display_sets.all():
            AnswerFactory(
                question=question,
                creator=editor,
                answer=answer,
                is_ground_truth=True,
                display_set=ds,
            )

    return rs


@pytest.fixture
def component_interfaces():
    interfaces = [
        {
            "title": "Boolean",
            "kind": ComponentInterface.Kind.BOOL,
            "relative_path": "bool",
        },
        {
            "title": "String",
            "kind": ComponentInterface.Kind.STRING,
            "relative_path": "string",
        },
        {
            "title": "Integer",
            "kind": ComponentInterface.Kind.INTEGER,
            "relative_path": "int",
        },
        {
            "title": "Float",
            "kind": ComponentInterface.Kind.FLOAT,
            "relative_path": "float",
        },
        {
            "title": "2D bounding box",
            "kind": ComponentInterface.Kind.TWO_D_BOUNDING_BOX,
            "relative_path": "2d_bounding_box",
        },
        {
            "title": "Multiple 2D bounding boxes",
            "kind": ComponentInterface.Kind.MULTIPLE_TWO_D_BOUNDING_BOXES,
            "relative_path": "multiple_2d_bounding_boxes",
        },
        {
            "title": "Distance measurement",
            "kind": ComponentInterface.Kind.DISTANCE_MEASUREMENT,
            "relative_path": "distance_measurement",
        },
        {
            "title": "Multiple distance measurements",
            "kind": ComponentInterface.Kind.MULTIPLE_DISTANCE_MEASUREMENTS,
            "relative_path": "multiple_distance_measurements",
        },
        {
            "title": "Point",
            "kind": ComponentInterface.Kind.POINT,
            "relative_path": "point",
        },
        {
            "title": "Multiple points",
            "kind": ComponentInterface.Kind.MULTIPLE_POINTS,
            "relative_path": "multiple_points",
        },
        {
            "title": "Polygon",
            "kind": ComponentInterface.Kind.POLYGON,
            "relative_path": "polygon",
        },
        {
            "title": "Multiple polygons",
            "kind": ComponentInterface.Kind.MULTIPLE_POLYGONS,
            "relative_path": "multiple_polygons",
        },
        {
            "title": "Anything",
            "kind": ComponentInterface.Kind.ANY,
            "relative_path": "any",
            "store_in_database": False,
        },
    ]

    return [ComponentInterfaceFactory(**interface) for interface in interfaces]


@pytest.fixture
def uploaded_image():
    return create_uploaded_image


@pytest.fixture
def challenge_reviewer():
    user = UserFactory()
    reviewers = Group.objects.get(
        name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
    )
    reviewers.user_set.add(user)
    return user


AUTH_URL = reverse_lazy("mfa_authenticate")


def do_totp_authentication(
    client,
    user,
    *,
    auth_url=AUTH_URL,
):
    device = Authenticator.objects.get(
        user=user, type=Authenticator.Type.RECOVERY_CODES
    )
    client.post(
        auth_url,
        {"code": device.wrap().get_unused_codes()[0]},
    )


@pytest.fixture
def authenticated_staff_user(client):
    user = UserFactory(username="john", is_staff=True)
    totp.TOTP.activate(user, totp.generate_totp_secret())
    recovery_codes.RecoveryCodes.activate(user)
    user = authenticate(
        username=user.username, password=SUPER_SECURE_TEST_PASSWORD
    )
    do_totp_authentication(
        client=client,
        user=user,
    )
    return user
