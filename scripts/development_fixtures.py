import base64
import itertools
import logging
import random

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import IntegrityError
from faker import Faker
from knox import crypto
from knox.models import AuthToken
from knox.settings import CONSTANTS
from machina.apps.forum.models import Forum

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.anatomy.models import BodyRegion, BodyStructure
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.challenges.models import Challenge, ChallengeSeries
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.direct_messages.models import Conversation, DirectMessage
from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
    Evaluation,
    Method,
    Phase,
    Submission,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.pages.models import Page
from grandchallenge.reader_studies.models import (
    Answer,
    DisplaySet,
    Question,
    QuestionWidgetKindChoices,
    ReaderStudy,
)
from grandchallenge.task_categories.models import TaskType
from grandchallenge.verifications.models import Verification
from grandchallenge.workstations.models import Workstation
from scripts.algorithm_evaluation_fixtures import _gc_demo_algorithm
from scripts.component_interface_value_fixtures import _create_image

logger = logging.getLogger(__name__)

DEFAULT_USERS = [
    "demo",
    "demop",
    "user",
    "admin",
    "readerstudy",
    "workstation",
    "algorithm",
    "algorithmuser",
    "archive",
]


def run():
    """Creates the main project, demo user and demo challenge."""
    print("🔨 Creating development fixtures 🔨")

    if not settings.DEBUG:
        raise RuntimeError(
            "Skipping this command, server is not in DEBUG mode."
        )

    try:
        users = _create_users(usernames=DEFAULT_USERS)
    except IntegrityError as e:
        raise RuntimeError("Fixtures already initialized") from e

    _create_direct_messages(users)
    _set_user_permissions(users)
    _create_task_types_regions_modalities(users)
    _create_workstation(users)
    algorithm = _create_algorithm_demo(users)
    _create_demo_challenge(users=users, algorithm=algorithm)
    _create_reader_studies(users)
    _create_archive(users)
    _create_user_tokens(users)
    _create_help_forum()
    _create_flatpages()

    print("✨ Development fixtures successfully created ✨")


def _create_flatpages():
    site = Site.objects.get(pk=settings.SITE_ID)
    page = FlatPage.objects.create(
        url="/about/",
        title="About us",
        content="<p>You can add flatpages via django admin</p>",
    )
    page.sites.add(site)


def _create_users(usernames):
    users = {}
    fake = Faker()

    for username in usernames:
        user = get_user_model().objects.create(
            username=username,
            email=f"{username}@example.com",
            is_active=True,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
        )
        user.set_password(username)
        user.save()

        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True,
        )

        Verification.objects.create(
            user=user,
            email=user.email,
            is_verified=True,
        )

        user.user_profile.institution = fake.company()
        user.user_profile.department = f"Department of {fake.job().title()}s"
        user.user_profile.country = fake.country_code()
        user.user_profile.receive_newsletter = True
        user.user_profile.save()
        users[username] = user

    return users


def _create_direct_messages(users):
    fake = Faker()

    for combination in itertools.combinations(users.values(), 2):
        conversation = Conversation.objects.create()
        conversation.participants.set(combination)

        unread = random.choice([True, False])

        for _ in range(5):
            sender = random.choice(combination)
            message = DirectMessage.objects.create(
                conversation=conversation,
                sender=sender,
                message=fake.text(max_nb_chars=160),
            )
            if unread:
                message.unread_by.set({*combination} - {sender})


def _set_user_permissions(users):
    users["admin"].is_staff = True
    users["admin"].save()

    rs_group = Group.objects.get(
        name=settings.READER_STUDY_CREATORS_GROUP_NAME
    )
    users["readerstudy"].groups.add(rs_group)

    workstation_group = Group.objects.get(
        name=settings.WORKSTATIONS_CREATORS_GROUP_NAME
    )
    users["workstation"].groups.add(workstation_group)
    users["workstation"].user_permissions.add(
        Permission.objects.get(codename="add_workstationconfig")
    )

    algorithm_group = Group.objects.get(
        name=settings.ALGORITHMS_CREATORS_GROUP_NAME
    )
    users["algorithm"].groups.add(algorithm_group)

    add_archive_perm = Permission.objects.get(codename="add_archive")
    users["archive"].user_permissions.add(add_archive_perm)
    users["demo"].user_permissions.add(add_archive_perm)


def _create_help_forum():
    Forum.objects.create(name="General", type=Forum.FORUM_POST)


def _create_demo_challenge(users, algorithm):
    demo = Challenge.objects.create(
        short_name="demo",
        description="Demo Challenge",
        creator=users["demo"],
        hidden=False,
        display_forum_link=True,
    )
    demo.add_participant(users["demop"])

    Page.objects.create(
        challenge=demo, display_title="all", permission_level="ALL"
    )
    Page.objects.create(
        challenge=demo, display_title="reg", permission_level="REG"
    )
    Page.objects.create(
        challenge=demo, display_title="adm", permission_level="ADM"
    )

    Phase.objects.create(challenge=demo, title="Phase 1")
    Phase.objects.create(challenge=demo, title="Phase 2")

    combined = CombinedLeaderboard.objects.create(
        title="overall", challenge=demo
    )
    combined.phases.set(demo.phase_set.all())

    for phase_num, phase in enumerate(demo.phase_set.all()):
        phase.score_title = "Accuracy ± std"
        phase.score_jsonpath = "acc.mean"
        phase.score_error_jsonpath = "acc.std"
        phase.extra_results_columns = [
            {
                "title": "Dice ± std",
                "path": "dice.mean",
                "error_path": "dice.std",
                "order": "desc",
            }
        ]
        if phase_num == 0:
            phase.submission_kind = SubmissionKindChoices.ALGORITHM
        phase.save()

        method = Method(phase=phase, creator=users["demo"])

        with _gc_demo_algorithm() as container:
            method.image.save("algorithm_io.tar", container)

        if phase_num == 1:
            submission = Submission(phase=phase, creator=users["demop"])
            content = ContentFile(base64.b64decode(b""))
            submission.predictions_file.save("test.csv", content)
        else:
            submission = Submission(
                phase=phase,
                creator=users["demop"],
                algorithm_image=algorithm.algorithm_container_images.first(),
            )
        submission.save()

        e = Evaluation.objects.create(
            submission=submission,
            method=method,
            status=Evaluation.SUCCESS,
            time_limit=submission.phase.evaluation_time_limit,
        )

        def create_result(evaluation, result: dict):
            interface = ComponentInterface.objects.get(
                slug="metrics-json-file"
            )

            try:
                output_civ = evaluation.outputs.get(interface=interface)
                output_civ.value = result
                output_civ.save()
            except ObjectDoesNotExist:
                output_civ = ComponentInterfaceValue.objects.create(
                    interface=interface, value=result
                )
                evaluation.outputs.add(output_civ)

        create_result(
            e,
            {
                "acc": {"mean": 0.1 * phase_num, "std": 0.1},
                "dice": {"mean": 0.71, "std": 0.05},
            },
        )


def _create_task_types_regions_modalities(users):
    TaskType.objects.create(type="Segmentation")
    TaskType.objects.create(type="Classification")

    regions_structures = {
        "Head and Neck": ["Brain", "Teeth"],
        "Thorax": ["Lung"],
        "Cardiac": ["Heart"],
        "Abdomen": ["Liver", "Pancreas", "Kidney", "Spleen"],
        "Pelvis": ["Prostate", "Cervix"],
        "Spine": ["Spinal Cord"],
        "Upper Limb": ["Hand"],
        "Lower Limb": ["Knee"],
    }

    for region, structures in regions_structures.items():
        r = BodyRegion.objects.create(region=region)
        for structure in structures:
            BodyStructure.objects.create(structure=structure, region=r)

    modalities = (
        "CT",
        "MR",
        "XR",
        "PET",
        "PET-CT",
        "PET-MR",
        "Mammography",
        "CT-MR",
        "US",
        "TEM",
        "Histology",
    )
    for modality in modalities:
        ImagingModality.objects.create(modality=modality)

    ChallengeSeries.objects.create(name="MICCAI")


def _create_algorithm_demo(users):

    (input_civ, _) = ComponentInterfaceValue.objects.get_or_create(
        interface=ComponentInterface.objects.get(slug="generic-medical-image"),
        image=_create_image(
            name="test_image.mha",
            width=10,
            height=10,
        ),
    )

    algorithm = Algorithm.objects.create(
        title="Test Algorithm",
        logo=create_uploaded_image(),
        repo_name="github-username/repo-name",
        contact_email="example@example.org",
        display_editors=True,
        result_template="{% for key, value in results.items() %}\n{{ key }}:  {{ value }}\n{% endfor %}",
    )
    algorithm.editors_group.user_set.add(users["algorithm"], users["demo"])
    algorithm.users_group.user_set.add(users["algorithmuser"])
    algorithm.inputs.set(
        [ComponentInterface.objects.get(slug="generic-medical-image")]
    )
    algorithm.outputs.set(
        [ComponentInterface.objects.get(slug="results-json-file")]
    )

    algorithm_image = AlgorithmImage(
        creator=users["algorithm"], algorithm=algorithm
    )

    with _gc_demo_algorithm() as container:
        algorithm_image.image.save("algorithm_io.tar", container)

    results = [
        {"score": 0.5},
        {"score": 0.6},
        {"score": 0.7},
    ]

    for result in results:
        algorithms_job = Job.objects.create(
            creator=users["algorithm"],
            algorithm_image=algorithm_image,
            status=Evaluation.SUCCESS,
            time_limit=60,
        )

        algorithms_job.inputs.add(input_civ)

        algorithms_job.outputs.add(
            ComponentInterfaceValue.objects.create(
                interface=ComponentInterface.objects.get(
                    slug="results-json-file"
                ),
                value=result,
            )
        )

    return algorithm


def _create_workstation(users):
    w = Workstation.objects.get(slug=settings.DEFAULT_WORKSTATION_SLUG)
    w.add_editor(user=users["workstation"])


def _create_reader_studies(users):
    reader_study = ReaderStudy.objects.create(
        title="Reader Study",
        workstation=Workstation.objects.last(),
        logo=create_uploaded_image(),
        description="Test reader study",
        view_content={"main": ["generic-medical-image"]},
    )
    reader_study.editors_group.user_set.add(users["readerstudy"])
    reader_study.readers_group.user_set.add(users["demo"])

    question = Question.objects.create(
        reader_study=reader_study,
        question_text="foo",
        answer_type=Question.AnswerType.TEXT,
        widget=QuestionWidgetKindChoices.TEXT_INPUT,
    )

    display_set = DisplaySet.objects.create(
        reader_study=reader_study,
    )
    image = _create_image(
        name="test_image2.mha",
        modality=ImagingModality.objects.get(modality="MR"),
        width=128,
        height=128,
        color_space="RGB",
    )

    annotation_interface = ComponentInterface(
        store_in_database=True,
        relative_path="annotation.json",
        slug="annotation",
        title="Annotation",
        kind=ComponentInterface.Kind.TWO_D_BOUNDING_BOX,
    )
    annotation_interface.save()
    civ = ComponentInterfaceValue.objects.create(
        interface=ComponentInterface.objects.get(slug="generic-medical-image"),
        image=image,
    )
    display_set.values.set([civ])

    answer = Answer.objects.create(
        creator=users["readerstudy"],
        question=question,
        answer="foo",
        display_set=display_set,
    )
    answer.save()


def _create_archive(users):
    archive = Archive.objects.create(
        title="Archive",
        workstation=Workstation.objects.last(),
        logo=create_uploaded_image(),
        description="Test archive",
    )
    archive.editors_group.user_set.add(users["archive"])
    archive.uploaders_group.user_set.add(users["demo"])

    item = ArchiveItem.objects.create(archive=archive)
    civ = ComponentInterfaceValue.objects.create(
        interface=ComponentInterface.objects.get(slug="generic-medical-image"),
        image=_create_image(
            name="test_image2.mha",
            modality=ImagingModality.objects.get(modality="MR"),
            width=128,
            height=128,
            color_space="RGB",
        ),
    )

    item.values.add(civ)


def _create_user_tokens(users):
    # Hard code tokens used in gcapi integration tests
    user_tokens = {
        "admin": "1b9436200001f2eaf57cd77db075cbb60a49a00a",
        "readerstudy": "01614a77b1c0b4ecd402be50a8ff96188d5b011d",
        "demop": "00aa710f4dc5621a0cb64b0795fbba02e39d7700",
        "archive": "0d284528953157759d26c469297afcf6fd367f71",
    }

    out = f"{'*' * 80}\n"
    for user, token in user_tokens.items():
        digest = crypto.hash_token(token)

        AuthToken(
            token_key=token[: CONSTANTS.TOKEN_KEY_LENGTH],
            digest=digest,
            user=users[user],
            expiry=None,
        ).save()

        out += f"\t{user} token is: {token}\n"
    out += f"{'*' * 80}\n"
    logger.debug(out)
