import os
import warnings
import zipfile
from collections import namedtuple
from pathlib import Path
from typing import NamedTuple

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from guardian.shortcuts import assign_perm
from requests import put

from grandchallenge.algorithms.models import Job
from grandchallenge.cases.widgets import ImageWidgetChoices
from grandchallenge.components.backends import docker_client
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    FileWidgetChoices,
)
from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.reader_studies.models import Question
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.cases_tests import RESOURCE_PATH
from tests.cases_tests.factories import (
    ImageFileFactoryWithMHDFile,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import (
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import ChallengeFactory, ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
)
from tests.verification_tests.factories import VerificationFactory
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


class AlgorithmWithInputsAndCIVs(NamedTuple):
    algorithm: AlgorithmFactory
    civs: [ComponentInterfaceValueFactory]


@pytest.fixture
def algorithm_with_image_and_model_and_two_inputs():
    alg = AlgorithmFactory(time_limit=123)
    AlgorithmImageFactory(
        algorithm=alg,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    AlgorithmModelFactory(algorithm=alg, is_desired_version=True)
    editor = UserFactory()
    alg.add_editor(editor)

    ci1, ci2 = ComponentInterfaceFactory.create_batch(
        2, kind=ComponentInterface.Kind.STRING
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[ci1, ci2], outputs=[ComponentInterfaceFactory()]
    )
    alg.interfaces.add(interface)
    civs = [
        ComponentInterfaceValueFactory(interface=ci1, value="foo"),
        ComponentInterfaceValueFactory(interface=ci2, value="bar"),
    ]

    return AlgorithmWithInputsAndCIVs(
        algorithm=alg,
        civs=civs,
    )


class AlgorithmWithInputs(NamedTuple):
    algorithm: AlgorithmFactory
    editor: UserFactory
    ci_str: ComponentInterfaceFactory
    ci_bool: ComponentInterfaceFactory
    ci_img_upload: ComponentInterfaceFactory
    ci_existing_img: ComponentInterfaceFactory
    ci_json_in_db_with_schema: ComponentInterfaceFactory
    ci_json_file: ComponentInterfaceFactory
    im_upload_through_api: RawImageUploadSessionFactory
    im_upload_through_ui: UserUploadFactory
    file_upload: UserUploadFactory
    image_1: ImageFactory
    image_2: ImageFactory


@pytest.fixture
def algorithm_with_multiple_inputs():
    algorithm = AlgorithmFactory(time_limit=600)
    AlgorithmImageFactory(
        algorithm=algorithm,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    AlgorithmModelFactory(
        algorithm=algorithm,
        is_desired_version=True,
    )

    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)
    algorithm.add_editor(user=user)

    # create interfaces of different kinds
    ci_str = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.STRING
    )
    ci_bool = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
    ci_img_upload = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.PANIMG_IMAGE
    )
    ci_existing_img = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.PANIMG_IMAGE
    )
    ci_json_in_db_with_schema = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY,
        store_in_database=True,
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "array",
        },
    )
    ci_json_file = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY,
        store_in_database=False,
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "array",
        },
    )

    # Create inputs
    im_upload_through_api = RawImageUploadSessionFactory(creator=user)
    image_1, image_2 = ImageFactory.create_batch(2)
    mhd1, mhd2 = ImageFileFactoryWithMHDFile.create_batch(2)
    image_1.files.set([mhd1])
    image_2.files.set([mhd2])
    for im in [image_1, image_2]:
        assign_perm("cases.view_image", user, im)
    im_upload_through_api.image_set.set([image_1])

    im_upload_through_ui = create_upload_from_file(
        file_path=RESOURCE_PATH / "image10x10x10.mha",
        creator=user,
    )

    file_upload = UserUploadFactory(filename="file.json", creator=user)
    presigned_urls = file_upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'["Foo", "bar"]')
    file_upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    file_upload.save()

    return AlgorithmWithInputs(
        algorithm=algorithm,
        editor=user,
        ci_str=ci_str,
        ci_bool=ci_bool,
        ci_img_upload=ci_img_upload,
        ci_existing_img=ci_existing_img,
        ci_json_in_db_with_schema=ci_json_in_db_with_schema,
        ci_json_file=ci_json_file,
        im_upload_through_api=im_upload_through_api,
        im_upload_through_ui=im_upload_through_ui,
        file_upload=file_upload,
        image_1=image_1,
        image_2=image_2,
    )


def get_interface_form_data(
    *,
    interface_slug,
    data,
    existing_data=False,
):
    ci = ComponentInterface.objects.get(slug=interface_slug)
    form_data = {f"{INTERFACE_FORM_FIELD_PREFIX}{interface_slug}": data}
    if ci.super_kind == ci.SuperKind.IMAGE:
        if existing_data:
            form_data[
                f"widget-choice-{INTERFACE_FORM_FIELD_PREFIX}{interface_slug}"
            ] = ImageWidgetChoices.IMAGE_SEARCH.name
        else:
            form_data[
                f"widget-choice-{INTERFACE_FORM_FIELD_PREFIX}{interface_slug}"
            ] = ImageWidgetChoices.IMAGE_UPLOAD.name
    elif ci.super_kind == ci.SuperKind.FILE:
        if existing_data:
            form_data[
                f"widget-choice-{INTERFACE_FORM_FIELD_PREFIX}{interface_slug}"
            ] = FileWidgetChoices.FILE_SEARCH.name
        else:
            form_data[
                f"widget-choice-{INTERFACE_FORM_FIELD_PREFIX}{interface_slug}"
            ] = FileWidgetChoices.FILE_UPLOAD.name

    return form_data


class InterfacesAndJobs(NamedTuple):
    archive: ArchiveFactory
    algorithm_image: AlgorithmImageFactory
    interface1: AlgorithmInterfaceFactory
    interface2: AlgorithmInterfaceFactory
    interface3: AlgorithmInterfaceFactory
    jobs_for_interface1: list[AlgorithmJobFactory]
    jobs_for_interface2: list[AlgorithmJobFactory]
    jobs_for_interface3: list[AlgorithmJobFactory]
    items_for_interface1: list[ArchiveItemFactory]
    items_for_interface2: list[ArchiveItemFactory]
    items_for_interface3: list[ArchiveItemFactory]
    civs_for_interface1: list[ComponentInterfaceValueFactory]
    civs_for_interface2: list[ComponentInterfaceValueFactory]
    civs_for_interface3: list[ComponentInterfaceValueFactory]
    output_civs: list[ComponentInterfaceValueFactory]


@pytest.fixture
def archive_items_and_jobs_for_interfaces():
    ci1, ci2, ci3 = ComponentInterfaceFactory.create_batch(3)

    interface1 = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci3])
    interface2 = AlgorithmInterfaceFactory(inputs=[ci1, ci2], outputs=[ci3])
    interface3 = AlgorithmInterfaceFactory(inputs=[ci1, ci3], outputs=[ci3])

    archive = ArchiveFactory()
    ai1, ai2, ai3, ai4, ai5, ai6 = ArchiveItemFactory.create_batch(
        6, archive=archive
    )

    civ_int_1a = ComponentInterfaceValueFactory(interface=ci1)
    civ_int_1b = ComponentInterfaceValueFactory(interface=ci1)
    civ_int_1c = ComponentInterfaceValueFactory(interface=ci1)
    civ_int_2a = ComponentInterfaceValueFactory(interface=ci2)
    civ_int_2b = ComponentInterfaceValueFactory(interface=ci2)
    civ_int_3a = ComponentInterfaceValueFactory(interface=ci3)

    civs_out = ComponentInterfaceValueFactory.create_batch(6, interface=ci3)

    ai1.values.set([civ_int_1a])  # valid for interface 1
    ai2.values.set([civ_int_1b])  # valid for interface 1
    ai3.values.set([civ_int_1c, civ_int_2a])  # valid for interface 2
    ai4.values.set([civ_int_1b, civ_int_2b])  # valid for interface 2
    ai5.values.set([civ_int_1a, civ_int_3a])  # valid for interface 3
    ai6.values.set([civ_int_3a])  # not valid for any interface

    algorithm_image = AlgorithmImageFactory()
    algorithm_image.algorithm.interfaces.set([interface1, interface2])

    # create jobs for interface 1
    j1, j2, j3 = AlgorithmJobFactory.create_batch(
        3,
        algorithm_image=algorithm_image,
        algorithm_interface=interface1,
        time_limit=algorithm_image.algorithm.time_limit,
        creator=None,
    )
    # outputs don't matter
    j1.inputs.set([civ_int_1a])  # corresponds to item ai1
    j2.inputs.set(
        [civ_int_1c]
    )  # matches interface1, but does not match an item (uses value from an item for interface2)
    j3.inputs.set(
        [ComponentInterfaceValueFactory(interface=ci1)]
    )  # matches interface1 but does not correspond to an item (new value)

    # create jobs for interface 2
    j4, j5, j6 = AlgorithmJobFactory.create_batch(
        3,
        algorithm_image=algorithm_image,
        algorithm_interface=interface2,
        time_limit=algorithm_image.algorithm.time_limit,
        creator=None,
    )
    j4.inputs.set([civ_int_1c, civ_int_2a])  # corresponds to item ai3
    j5.inputs.set(
        [civ_int_1a, civ_int_2a]
    )  # valid for interface 2 but does not correspond to an item (mixes values from different items)
    j6.inputs.set(
        [
            ComponentInterfaceValueFactory(interface=ci1),
            ComponentInterfaceValueFactory(interface=ci2),
        ]
    )  # valid for interface 2 but does not correspond to an item (new values)

    # create jobs for interface 3 (which is not configured for the algorithm)
    (
        j7,
        j8,
    ) = AlgorithmJobFactory.create_batch(
        2,
        algorithm_image=algorithm_image,
        algorithm_interface=interface3,
        time_limit=algorithm_image.algorithm.time_limit,
        creator=None,
    )
    j7.inputs.set(
        [civ_int_1a, civ_int_3a]
    )  # valid for interface3, corresponds to item ai5
    j8.inputs.set(
        [civ_int_1b, civ_int_3a]
    )  # valid for interface3, but does not match item

    return InterfacesAndJobs(
        archive=archive,
        algorithm_image=algorithm_image,
        interface1=interface1,
        interface2=interface2,
        interface3=interface3,
        jobs_for_interface1=[j1, j2, j3],
        jobs_for_interface2=[j4, j5, j6],
        jobs_for_interface3=[j7, j8],
        items_for_interface1=[ai1, ai2],
        items_for_interface2=[ai3, ai4],
        items_for_interface3=[ai5],
        civs_for_interface1=[civ_int_1a, civ_int_1b, civ_int_1c],
        civs_for_interface2=[
            [civ_int_1c, civ_int_2a],
            [civ_int_1b, civ_int_2b],
        ],
        civs_for_interface3=[civ_int_3a],
        output_civs=civs_out,
    )


@pytest.fixture
def jobs_for_optional_inputs(archive_items_and_jobs_for_interfaces):
    # delete existing jobs
    Job.objects.all().delete()

    # create 2 successful jobs per interface, for each of the archive items
    j1, j2 = AlgorithmJobFactory.create_batch(
        2,
        status=Job.SUCCESS,
        creator=None,
        algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
        algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
        time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
    )
    j1.inputs.set(
        [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
    )
    j1.outputs.set([archive_items_and_jobs_for_interfaces.output_civs[0]])
    j2.inputs.set(
        [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
    )
    j2.outputs.set([archive_items_and_jobs_for_interfaces.output_civs[1]])

    # create 2 jobs per interface, for each of the archive items
    j3, j4 = AlgorithmJobFactory.create_batch(
        2,
        status=Job.SUCCESS,
        creator=None,
        algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
        algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
        time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
    )
    j3.inputs.set(archive_items_and_jobs_for_interfaces.civs_for_interface2[0])
    j3.outputs.set([archive_items_and_jobs_for_interfaces.output_civs[2]])
    j4.inputs.set(archive_items_and_jobs_for_interfaces.civs_for_interface2[1])
    j4.outputs.set([archive_items_and_jobs_for_interfaces.output_civs[3]])

    return InterfacesAndJobs(
        archive=archive_items_and_jobs_for_interfaces.archive,
        algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
        interface1=archive_items_and_jobs_for_interfaces.interface1,
        interface2=archive_items_and_jobs_for_interfaces.interface2,
        interface3=archive_items_and_jobs_for_interfaces.interface3,
        jobs_for_interface1=[j1, j2],
        jobs_for_interface2=[j3, j4],
        jobs_for_interface3=[],
        items_for_interface1=archive_items_and_jobs_for_interfaces.items_for_interface1,
        items_for_interface2=archive_items_and_jobs_for_interfaces.items_for_interface2,
        items_for_interface3=archive_items_and_jobs_for_interfaces.items_for_interface3,
        civs_for_interface1=archive_items_and_jobs_for_interfaces.civs_for_interface1,
        civs_for_interface2=archive_items_and_jobs_for_interfaces.civs_for_interface2,
        civs_for_interface3=archive_items_and_jobs_for_interfaces.civs_for_interface3,
        output_civs=archive_items_and_jobs_for_interfaces.output_civs[:4],
    )


class SubmissionWithJobs(NamedTuple):
    submission: SubmissionFactory
    jobs: list[AlgorithmJobFactory]
    interface1: AlgorithmInterfaceFactory
    interface2: AlgorithmInterfaceFactory
    civs_for_interface1: list[ComponentInterfaceValueFactory]
    civs_for_interface2: list[ComponentInterfaceValueFactory]
    output_civs: list[ComponentInterfaceValueFactory]


@pytest.fixture
def submission_without_model_for_optional_inputs(jobs_for_optional_inputs):
    submission = SubmissionFactory(
        algorithm_image=jobs_for_optional_inputs.algorithm_image
    )
    submission.phase.archive = jobs_for_optional_inputs.archive
    submission.phase.save()
    submission.phase.algorithm_interfaces.set(
        [
            jobs_for_optional_inputs.interface1,
            jobs_for_optional_inputs.interface2,
        ]
    )
    return SubmissionWithJobs(
        submission=submission,
        jobs=[
            *jobs_for_optional_inputs.jobs_for_interface1,
            *jobs_for_optional_inputs.jobs_for_interface2,
        ],
        interface1=jobs_for_optional_inputs.interface1,
        interface2=jobs_for_optional_inputs.interface2,
        civs_for_interface1=jobs_for_optional_inputs.civs_for_interface1,
        civs_for_interface2=jobs_for_optional_inputs.civs_for_interface2,
        output_civs=jobs_for_optional_inputs.output_civs,
    )


@pytest.fixture
def submission_with_model_for_optional_inputs(jobs_for_optional_inputs):
    submission_with_model = SubmissionFactory(
        algorithm_image=jobs_for_optional_inputs.algorithm_image,
        algorithm_model=AlgorithmModelFactory(
            algorithm=jobs_for_optional_inputs.algorithm_image.algorithm
        ),
    )
    submission_with_model.phase.archive = jobs_for_optional_inputs.archive
    submission_with_model.phase.save()
    submission_with_model.phase.algorithm_interfaces.set(
        [
            jobs_for_optional_inputs.interface1,
            jobs_for_optional_inputs.interface2,
        ]
    )
    return SubmissionWithJobs(
        submission=submission_with_model,
        jobs=[
            *jobs_for_optional_inputs.jobs_for_interface1,
            *jobs_for_optional_inputs.jobs_for_interface2,
        ],
        interface1=jobs_for_optional_inputs.interface1,
        interface2=jobs_for_optional_inputs.interface2,
        civs_for_interface1=jobs_for_optional_inputs.civs_for_interface1,
        civs_for_interface2=jobs_for_optional_inputs.civs_for_interface2,
        output_civs=jobs_for_optional_inputs.output_civs,
    )
