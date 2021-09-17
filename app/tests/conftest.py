import os
import zipfile
from collections import namedtuple
from pathlib import Path
from subprocess import call
from typing import List, NamedTuple

import docker
import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site

from grandchallenge.cases.models import Image
from grandchallenge.components.models import ComponentInterface
from grandchallenge.reader_studies.models import Question
from tests.annotations_tests.factories import (
    BooleanClassificationAnnotationFactory,
    CoordinateListAnnotationFactory,
    ETDRSGridAnnotationFactory,
    ImagePathologyAnnotationFactory,
    ImageQualityAnnotationFactory,
    ImageTextAnnotationFactory,
    IntegerClassificationAnnotationFactory,
    LandmarkAnnotationSetFactory,
    MeasurementAnnotationFactory,
    OctRetinaImagePathologyAnnotationFactory,
    PolygonAnnotationSetFactory,
    RetinaImagePathologyAnnotationFactory,
    SingleLandmarkAnnotationFactory,
    SinglePolygonAnnotationFactory,
)
from tests.archives_tests.factories import ArchiveFactory
from tests.archives_tests.test_models import create_archive_items_for_images
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import MethodFactory
from tests.factories import (
    ChallengeFactory,
    ImageFactory,
    UserFactory,
)
from tests.fixtures import create_uploaded_image
from tests.patients_tests.factories import PatientFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.studies_tests.factories import StudyFactory
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


@pytest.fixture(scope="session")
def docker_client():
    return docker.DockerClient(base_url=settings.COMPONENTS_DOCKER_BASE_URL)


@pytest.fixture(scope="session")
def docker_api_client():
    return docker.APIClient(base_url=settings.COMPONENTS_DOCKER_BASE_URL)


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
    challenge_set.challenge.use_evaluation = True
    challenge_set.challenge.save()

    phase = challenge_set.challenge.phase_set.get()

    method = MethodFactory(phase=phase, creator=challenge_set.creator)

    return eval_challenge_set(challenge_set, method)


def docker_image(
    tmpdir_factory,
    docker_client,
    docker_api_client,
    path,
    label,
    full_path=None,
):
    """Create the docker container."""
    if not full_path:
        full_path = os.path.join(
            os.path.split(__file__)[0], path, "resources", "docker",
        )
    im, _ = docker_client.images.build(
        path=full_path, tag=f"test-{label}:latest",
    )
    assert im.id in [x.id for x in docker_client.images.list()]
    image = docker_api_client.get_image(f"test-{label}:latest")
    outfile = tmpdir_factory.mktemp("docker").join(f"{label}-latest.tar")

    with outfile.open(mode="wb") as f:
        for chunk in image:
            f.write(chunk)

    docker_client.images.remove(image=im.id)

    call(["gzip", outfile])

    assert im.id not in [x.id for x in docker_client.images.list()]
    return f"{outfile}.gz", im.id


@pytest.fixture(scope="session")
def evaluation_image(tmpdir_factory, docker_client, docker_api_client):
    """Create the example evaluation container."""
    return docker_image(
        tmpdir_factory,
        docker_client,
        docker_api_client,
        path="evaluation_tests",
        label="evaluation",
    )


@pytest.fixture(scope="session")
def algorithm_image(tmpdir_factory, docker_client, docker_api_client):
    """Create the example algorithm container."""
    return docker_image(
        tmpdir_factory,
        docker_client,
        docker_api_client,
        path="algorithms_tests",
        label="algorithm",
    )


@pytest.fixture(scope="session")
def algorithm_io_image(tmpdir_factory, docker_client, docker_api_client):
    """Create the example algorithm container."""
    return docker_image(
        tmpdir_factory,
        docker_client,
        docker_api_client,
        path="",
        label="algorithm-io",
        full_path=os.path.join(
            os.path.split(__file__)[0], "resources", "gc_demo_algorithm",
        ),
    )


@pytest.fixture(scope="session")
def alpine_images(tmpdir_factory, docker_client, docker_api_client):
    docker_client.images.pull("alpine:3.12")
    docker_client.images.pull("alpine:3.11")

    # get all images and put them in a tar archive
    image = docker_api_client.get_image("alpine")
    outfile = tmpdir_factory.mktemp("alpine").join("alpine_multi.tar")

    with outfile.open("wb") as f:
        for chunk in image:
            f.write(chunk)

    return outfile


@pytest.fixture(scope="session")
def root_image(tmpdir_factory, docker_client, docker_api_client):
    docker_client.images.pull("alpine:3.8")

    image = docker_api_client.get_image("alpine:3.8")
    outfile = tmpdir_factory.mktemp("alpine").join("alpine.tar")

    with outfile.open("wb") as f:
        for chunk in image:
            f.write(chunk)

    return outfile


@pytest.fixture(scope="session")
def http_image(tmpdir_factory, docker_client, docker_api_client):
    image_name = "crccheck/hello-world"

    docker_client.images.pull(image_name)
    sha_256 = docker_client.images.get(image_name).id

    image = docker_api_client.get_image(image_name)
    outfile = tmpdir_factory.mktemp("http").join("http.tar")

    with outfile.open("wb") as f:
        for chunk in image:
            f.write(chunk)

    return outfile, sha_256


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


def add_to_graders_group(users):
    # Add to retina_graders group
    for grader in users:
        grader.groups.add(
            Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
        )


class AnnotationSet(NamedTuple):
    grader: UserFactory
    measurement: MeasurementAnnotationFactory
    boolean: BooleanClassificationAnnotationFactory
    integer: IntegerClassificationAnnotationFactory
    polygon: PolygonAnnotationSetFactory
    coordinatelist: CoordinateListAnnotationFactory
    landmark: LandmarkAnnotationSetFactory
    singlelandmarks: List
    etdrs: ETDRSGridAnnotationFactory


def generate_annotation_set(retina_grader=False, image=False):
    grader = UserFactory()

    if retina_grader:
        add_to_graders_group([grader])

    create_options = {"grader": grader}
    if image:
        create_options_with_image = {"image": image, **create_options}
    else:
        create_options_with_image = create_options

    measurement = MeasurementAnnotationFactory(**create_options_with_image)
    boolean = BooleanClassificationAnnotationFactory(
        **create_options_with_image
    )
    integer = IntegerClassificationAnnotationFactory(
        **create_options_with_image
    )
    polygon = PolygonAnnotationSetFactory(**create_options_with_image)
    coordinatelist = CoordinateListAnnotationFactory(
        **create_options_with_image
    )
    etdrs = ETDRSGridAnnotationFactory(**create_options_with_image)
    landmark = LandmarkAnnotationSetFactory(**create_options)

    # Create child models for polygon annotation set
    SinglePolygonAnnotationFactory.create_batch(10, annotation_set=polygon)

    # Create child models for landmark annotation set (3 per image)
    single_landmarks = []
    for i in range(5):
        if i > 0 or not image:
            image = ImageFactory()
        single_landmarks.append(
            SingleLandmarkAnnotationFactory(
                annotation_set=landmark, image=image
            )
        )

    return AnnotationSet(
        grader=grader,
        measurement=measurement,
        boolean=boolean,
        polygon=polygon,
        coordinatelist=coordinatelist,
        landmark=landmark,
        singlelandmarks=single_landmarks,
        etdrs=etdrs,
        integer=integer,
    )


@pytest.fixture(name="annotation_set")
def annotation_set():
    """
    Create a user with the one of each of the following annotations:
    Measurement, BooleanClassification, PolygonAnnotationSet (with 10 child
    annotations), CoordinateList, LandmarkAnnotationSet(with single landmark
    annotations for 5 images), ETDRSGrid.
    """
    return generate_annotation_set()


@pytest.fixture(name="annotation_set_for_image")
def annotation_set_for_image():
    """
    Create a user with the one of each of the following annotations:
    Measurement, BooleanClassification, PolygonAnnotationSet (with 10 child
    annotations), CoordinateList, LandmarkAnnotationSet(with single landmark
    annotations for 5 images), ETDRSGrid.
    """
    return generate_annotation_set


class TwoPolygonAnnotationSets(NamedTuple):
    grader1: UserFactory
    grader2: UserFactory
    polygonset1: PolygonAnnotationSetFactory
    polygonset2: PolygonAnnotationSetFactory


def generate_two_polygon_annotation_sets(retina_grader=False):
    graders = (UserFactory(), UserFactory())

    if retina_grader:
        add_to_graders_group(graders)

    polygonsets = (
        PolygonAnnotationSetFactory(grader=graders[0]),
        PolygonAnnotationSetFactory(grader=graders[1]),
    )

    # Create child models for polygon annotation set
    SinglePolygonAnnotationFactory.create_batch(
        10, annotation_set=polygonsets[0]
    )
    SinglePolygonAnnotationFactory.create_batch(
        10, annotation_set=polygonsets[1]
    )

    return TwoPolygonAnnotationSets(
        grader1=graders[0],
        grader2=graders[1],
        polygonset1=polygonsets[0],
        polygonset2=polygonsets[1],
    )


@pytest.fixture(name="two_retina_polygon_annotation_sets")
def two_retina_polygon_annotation_sets():
    """
    Create two PolygonAnnotationSets of each 10 SinglePolygonAnnotations
    belonging to two different graders that both are in the retina_graders
    group.
    """
    return generate_two_polygon_annotation_sets(retina_grader=True)


class MultipleLandmarkAnnotationSets(NamedTuple):
    grader1: UserFactory
    grader2: UserFactory
    grader3: UserFactory
    landmarkset1: LandmarkAnnotationSetFactory
    landmarkset1images: List
    landmarkset2: LandmarkAnnotationSetFactory
    landmarkset2images: List
    landmarkset3: LandmarkAnnotationSetFactory
    landmarkset3images: List
    landmarkset4: LandmarkAnnotationSetFactory
    landmarkset4images: List


def generate_multiple_landmark_annotation_sets(retina_grader=False):
    graders = (UserFactory(), UserFactory(), UserFactory())

    if retina_grader:
        add_to_graders_group(graders)

    landmarksets = (
        LandmarkAnnotationSetFactory(grader=graders[0]),
        LandmarkAnnotationSetFactory(grader=graders[1]),
        LandmarkAnnotationSetFactory(grader=graders[0]),
        LandmarkAnnotationSetFactory(grader=graders[2]),
    )

    # Create child models for landmark annotation set
    singlelandmarkbatches = (
        SingleLandmarkAnnotationFactory.create_batch(
            2, annotation_set=landmarksets[0]
        ),
        SingleLandmarkAnnotationFactory.create_batch(
            5, annotation_set=landmarksets[1]
        ),
        [],
        [],
    )

    images = [
        Image.objects.filter(
            singlelandmarkannotation__annotation_set=landmarksets[0].id
        ),
        Image.objects.filter(
            singlelandmarkannotation__annotation_set=landmarksets[1].id
        ),
        [],
        [],
    ]

    # Create singlelandmarkannotations with the images of landmarkset1
    for image in images[0]:
        singlelandmarkbatches[2].append(
            SingleLandmarkAnnotationFactory.create(
                annotation_set=landmarksets[2], image=image
            )
        )
        images[2].append(image)

        singlelandmarkbatches[3].append(
            SingleLandmarkAnnotationFactory.create(
                annotation_set=landmarksets[3], image=image
            )
        )
        images[3].append(image)
    singlelandmarkbatches[2].append(
        SingleLandmarkAnnotationFactory.create(annotation_set=landmarksets[2])
    )
    images[2].append(singlelandmarkbatches[2][-1].image)

    return MultipleLandmarkAnnotationSets(
        grader1=graders[0],
        grader2=graders[1],
        grader3=graders[2],
        landmarkset1=landmarksets[0],
        landmarkset1images=images[0],
        landmarkset2=landmarksets[1],
        landmarkset2images=images[1],
        landmarkset3=landmarksets[2],
        landmarkset3images=images[2],
        landmarkset4=landmarksets[3],
        landmarkset4images=images[3],
    )


@pytest.fixture(name="multiple_landmark_retina_annotation_sets")
def multiple_landmark_retina_annotation_sets():
    return generate_multiple_landmark_annotation_sets(retina_grader=True)


@pytest.fixture(name="multiple_landmark_annotation_sets")
def multiple_landmark_annotation_sets():
    return generate_multiple_landmark_annotation_sets(retina_grader=False)


class MultipleETDRSAnnotations(NamedTuple):
    grader1: UserFactory
    grader2: UserFactory
    etdrss1: List
    etdrss2: List


def generate_multiple_etdrs_annotations(retina_grader=False):
    graders = (UserFactory(), UserFactory())

    if retina_grader:
        add_to_graders_group(graders)

    etdrss1 = ETDRSGridAnnotationFactory.create_batch(10, grader=graders[0])
    etdrss2 = ETDRSGridAnnotationFactory.create_batch(5, grader=graders[1])

    return MultipleETDRSAnnotations(
        grader1=graders[0],
        grader2=graders[1],
        etdrss1=etdrss1,
        etdrss2=etdrss2,
    )


@pytest.fixture(name="multiple_retina_etdrs_annotations")
def multiple_retina_etdrs_annotations():
    """Creates 2 retina_grader users with 10 and 5 etdrs annotations."""
    return generate_multiple_etdrs_annotations(retina_grader=True)


@pytest.fixture(name="MultipleETDRSAnnotations")
def multiple_etdrs_annotations():
    """Creates 2 users with 10 and 5 etdrs annotations."""
    return generate_multiple_etdrs_annotations(retina_grader=False)


class ArchivePatientStudyImageSet(NamedTuple):
    archive1: ArchiveFactory
    patient11: PatientFactory
    patient12: PatientFactory
    study111: StudyFactory
    study112: StudyFactory
    study113: StudyFactory
    study121: StudyFactory
    study122: StudyFactory
    images111: List
    images112: List
    images113: List
    images121: List
    images122: List
    archive2: ArchiveFactory
    images211: List


def generate_archive_patient_study_image_set():
    patient11 = PatientFactory()
    patient12 = PatientFactory()
    study111 = StudyFactory(patient=patient11)
    study112 = StudyFactory(patient=patient11)
    study113 = StudyFactory(patient=patient11)
    study121 = StudyFactory(patient=patient12)
    study122 = StudyFactory(patient=patient12)
    images111 = ImageFactoryWithImageFile.create_batch(4, study=study111)
    images112 = ImageFactoryWithImageFile.create_batch(5, study=study112)
    images113 = ImageFactoryWithImageFile.create_batch(6, study=study113)
    images121 = ImageFactoryWithImageFile.create_batch(2, study=study121)
    images122 = ImageFactoryWithImageFile.create_batch(3, study=study122)
    images211 = ImageFactoryWithImageFile.create_batch(4, study=None)

    archive1, archive2 = ArchiveFactory.create_batch(2)

    create_archive_items_for_images(images111, archive1)
    create_archive_items_for_images(images112, archive1)
    create_archive_items_for_images(images113, archive1)
    create_archive_items_for_images(images121, archive1)
    create_archive_items_for_images(images122, archive1)
    create_archive_items_for_images(images211, archive2)

    return ArchivePatientStudyImageSet(
        archive1=archive1,
        patient11=patient11,
        patient12=patient12,
        study111=study111,
        study112=study112,
        study113=study113,
        study121=study121,
        study122=study122,
        images111=images111,
        images112=images112,
        images113=images113,
        images121=images121,
        images122=images122,
        archive2=archive2,
        images211=images211,
    )


@pytest.fixture(name="archive_patient_study_image_set")
def archive_patient_study_images_set():
    """
    Creates fixture archives.

    This fixture has one with 2 patients, with 3 (4, 5 and 6 images) and 2
    (2 and 3 images) studies, and another archive with one patient, one study
    and 4 images.
    """
    return generate_archive_patient_study_image_set()


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
    rs.images.set([im1, im2])
    rs.hanging_list = [{"main": im1.name}, {"main": im2.name}]
    rs.save()

    for question in [q1, q2, q3]:
        for im in [im1, im2]:
            ans = AnswerFactory(
                question=question,
                creator=editor,
                answer=True,
                is_ground_truth=True,
            )
            ans.images.add(im)

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
    images = reader_study_with_gt.images.all()
    for question, answer in [
        (q_choice, c_options[0].id),
        (q_multiple_choice, [mc_options[0].id, mc_options[1].id]),
    ]:
        ans = AnswerFactory(
            question=question,
            creator=editor,
            answer=answer,
            is_ground_truth=True,
        )
        for im in images:
            ans.images.add(im)

    return rs


@pytest.fixture
def image_with_image_level_annotations():
    grader = UserFactory()
    add_to_graders_group([grader])
    image = ImageFactory()
    factory_kwargs = {"image": image, "grader": grader}
    annotations = {
        "quality": ImageQualityAnnotationFactory(**factory_kwargs),
        "pathology": ImagePathologyAnnotationFactory(**factory_kwargs),
        "retina_pathology": RetinaImagePathologyAnnotationFactory(
            **factory_kwargs
        ),
        "oct_retina_pathology": OctRetinaImagePathologyAnnotationFactory(
            **factory_kwargs
        ),
        "text": ImageTextAnnotationFactory(**factory_kwargs),
    }
    return image, grader, annotations


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
    ]

    return [ComponentInterfaceFactory(**interface) for interface in interfaces]


@pytest.fixture
def uploaded_image():
    return create_uploaded_image
