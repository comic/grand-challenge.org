import base64
import json
import logging
import os
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.utils import timezone
from guardian.shortcuts import assign_perm
from knox import crypto
from knox.models import AuthToken
from knox.settings import CONSTANTS
from machina.apps.forum.models import Forum

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.anatomy.models import BodyRegion, BodyStructure
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeSeries,
    ExternalChallenge,
)
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.evaluation.models import (
    Evaluation,
    Method,
    Phase,
    Submission,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.github.models import GitHubUserToken, GitHubWebhookMessage
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.pages.models import Page
from grandchallenge.reader_studies.models import (
    Answer,
    DisplaySet,
    Question,
    ReaderStudy,
)
from grandchallenge.task_categories.models import TaskType
from grandchallenge.verifications.models import Verification
from grandchallenge.workstations.models import Workstation

logger = logging.getLogger(__name__)

DEFAULT_USERS = [
    "demo",
    "demop",
    "user",
    "admin",
    "retina",
    "readerstudy",
    "workstation",
    "algorithm",
    "algorithmuser",
    "air",
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

    _set_user_permissions(users)
    _create_demo_challenge(users)
    _create_external_challenge(users)
    _create_workstation(users)
    _create_algorithm_demo(users)
    _create_reader_studies(users)
    _create_archive(users)
    _create_user_tokens(users)
    _create_github_user_token(users["algorithm"])
    _create_github_webhook_message()
    _create_help_forum()
    _create_flatpages()
    _set_statistics_cache()

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

    for username in usernames:
        user = get_user_model().objects.create(
            username=username, email=f"{username}@example.com", is_active=True
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
            user=user, is_verified=True, email=user.email
        )
        user.user_profile.receive_newsletter = True
        user.user_profile.save()
        users[username] = user

    return users


def _set_user_permissions(users):
    users["admin"].is_staff = True
    users["admin"].save()

    retina_group = Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
    users["retina"].groups.add(retina_group)

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

    add_product_perm = Permission.objects.get(codename="add_product")
    users["air"].user_permissions.add(add_product_perm)

    add_archive_perm = Permission.objects.get(codename="add_archive")
    users["archive"].user_permissions.add(add_archive_perm)
    users["demo"].user_permissions.add(add_archive_perm)


def _create_help_forum():
    Forum.objects.create(name="General", type=Forum.FORUM_POST)


def _create_demo_challenge(users):
    demo = Challenge.objects.create(
        short_name="demo",
        description="demo project",
        creator=users["demo"],
        use_workspaces=True,
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

    Phase.objects.create(challenge=demo, title="Phase 2")

    for phase_num, phase in enumerate(demo.phase_set.all()):

        assign_perm("create_phase_workspace", users["demop"], phase)

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
        container = ContentFile(base64.b64decode(b""))
        method.image.save("test.tar", container)
        method.save()

        submission = Submission(phase=phase, creator=users["demop"])
        content = ContentFile(base64.b64decode(b""))
        submission.predictions_file.save("test.csv", content)
        submission.save()

        e = Evaluation.objects.create(
            submission=submission, method=method, status=Evaluation.SUCCESS
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


def _create_external_challenge(users):
    ex_challenge = ExternalChallenge.objects.create(
        creator=users["demo"],
        homepage="https://www.example.com",
        short_name="EXAMPLE2018",
        title="Example External Challenge 2018",
        description="An example of an external challenge",
        event_name="Example Event",
        event_url="https://www.example.com/2018",
        hidden=False,
    )

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

    s = ChallengeSeries.objects.create(name="MICCAI")

    mr_modality = ImagingModality.objects.get(modality="MR")
    ex_challenge.modalities.add(mr_modality)
    ex_challenge.series.add(s)
    ex_challenge.save()


def _create_github_user_token(user):
    now = timezone.now()
    GitHubUserToken.objects.create(
        user=user,
        access_token="ghu_tOkEn",
        access_token_expires=now + timedelta(hours=8),
        refresh_token="ghr_r3fR3sh",
        refresh_token_expires=now + timedelta(days=7),
    )


def _create_github_webhook_message():
    payload = {
        "action": "created",
        "sender": {
            "id": 1,
            "url": "https://api.github.com/users/repo-name",
            "type": "User",
            "login": "repo-name",
            "node_id": "MDQ6VXNlcjU3MjU3MTMw",
            "html_url": "https://github.com/repo-name",
            "gists_url": "https://api.github.com/users/repo-name/gists{/gist_id}",
            "repos_url": "https://api.github.com/users/repo-name/repos",
            "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
            "events_url": "https://api.github.com/users/repo-name/events{/privacy}",
            "site_admin": False,
            "gravatar_id": "",
            "starred_url": "https://api.github.com/users/repo-name/starred{/owner}{/repo}",
            "followers_url": "https://api.github.com/users/repo-name/followers",
            "following_url": "https://api.github.com/users/repo-name/following{/other_user}",
            "organizations_url": "https://api.github.com/users/repo-name/orgs",
            "subscriptions_url": "https://api.github.com/users/repo-name/subscriptions",
            "received_events_url": "https://api.github.com/users/repo-name/received_events",
        },
        "requester": None,
        "installation": {
            "id": 2,
            "app_id": 3,
            "events": ["create"],
            "account": {
                "id": 1,
                "url": "https://api.github.com/users/repo-name",
                "type": "User",
                "login": "repo-name",
                "node_id": "MDQ6VXNlcjU3MjU3MTMw",
                "html_url": "https://github.com/repo-name",
                "gists_url": "https://api.github.com/users/repo-name/gists{/gist_id}",
                "repos_url": "https://api.github.com/users/repo-name/repos",
                "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
                "events_url": "https://api.github.com/users/repo-name/events{/privacy}",
                "site_admin": False,
                "gravatar_id": "",
                "starred_url": "https://api.github.com/users/repo-name/starred{/owner}{/repo}",
                "followers_url": "https://api.github.com/users/repo-name/followers",
                "following_url": "https://api.github.com/users/repo-name/following{/other_user}",
                "organizations_url": "https://api.github.com/users/repo-name/orgs",
                "subscriptions_url": "https://api.github.com/users/repo-name/subscriptions",
                "received_events_url": "https://api.github.com/users/repo-name/received_events",
            },
            "app_slug": "app-name",
            "html_url": "https://github.com/settings/installations/2",
            "target_id": 1,
            "created_at": "2021-09-07T13:14:24.000+02:00",
            "updated_at": "2021-09-07T13:14:24.000+02:00",
            "permissions": {"contents": "read", "metadata": "read"},
            "target_type": "User",
            "suspended_at": None,
            "suspended_by": None,
            "repositories_url": "https://api.github.com/installation/repositories",
            "single_file_name": None,
            "access_tokens_url": "https://api.github.com/app/installations/2/access_tokens",
            "single_file_paths": [],
            "repository_selection": "selected",
            "has_multiple_single_files": False,
        },
        "repositories": [
            {
                "id": 377787003,
                "name": "private-3",
                "node_id": "MDEwOlJlcG9zaXRvcnkzNzc3ODcwMDM=",
                "private": True,
                "full_name": "repo-name/private-3",
            }
        ],
    }
    GitHubWebhookMessage.objects.create(payload=payload)


def _create_algorithm_demo(users):
    cases_image = Image(
        name="test_image.mha",
        modality=ImagingModality.objects.get(modality="MR"),
        width=128,
        height=128,
        color_space="RGB",
    )
    cases_image.save()

    algorithm = Algorithm.objects.create(
        title="Test Algorithm", logo=create_uploaded_image()
    )
    algorithm.editors_group.user_set.add(users["algorithm"], users["demo"])
    algorithm.users_group.user_set.add(users["algorithmuser"])
    algorithm.result_template = (
        "{% for key, value in results.metrics.items() -%}"
        "{{ key }}  {{ value }}"
        "{% endfor %}"
    )
    detection_interface = ComponentInterface(
        store_in_database=False,
        relative_path="detection_results.json",
        slug="detection-results",
        title="Detection Results",
        kind=ComponentInterface.Kind.ANY,
    )
    detection_interface.save()
    algorithm.outputs.add(detection_interface)
    algorithm_image = AlgorithmImage(
        creator=users["algorithm"], algorithm=algorithm
    )

    try:
        with open(
            os.path.join(settings.SITE_ROOT, "algorithm.tar.gz"), "rb"
        ) as f:
            container = File(f)
            algorithm_image.image.save("test_algorithm.tar", container)
    except FileNotFoundError:
        pass

    algorithm_image.save()

    results = [
        {"cancer_score": 0.5},
        {"cancer_score": 0.6},
        {"cancer_score": 0.7},
    ]

    detections = [
        {
            "detected points": [
                {"type": "Point", "start": [0, 1, 2], "end": [3, 4, 5]}
            ]
        },
        {
            "detected points": [
                {"type": "Point", "start": [6, 7, 8], "end": [9, 10, 11]}
            ]
        },
        {
            "detected points": [
                {"type": "Point", "start": [12, 13, 14], "end": [15, 16, 17]}
            ]
        },
    ]
    for res, det in zip(results, detections, strict=True):
        _create_job_result(users, algorithm_image, cases_image, res, det)


def _create_job_result(users, algorithm_image, cases_image, result, detection):
    algorithms_job = Job(
        creator=users["algorithm"],
        algorithm_image=algorithm_image,
        status=Evaluation.SUCCESS,
    )
    algorithms_job.save()
    algorithms_job.inputs.add(
        ComponentInterfaceValue.objects.create(
            interface=ComponentInterface.objects.get(
                slug="generic-medical-image"
            ),
            image=cases_image,
        )
    )
    algorithms_job.outputs.add(
        ComponentInterfaceValue.objects.create(
            interface=ComponentInterface.objects.get(slug="results-json-file"),
            value=result,
        )
    )
    civ = ComponentInterfaceValue.objects.create(
        interface=ComponentInterface.objects.get(slug="detection-results")
    )
    civ.file.save(
        "detection_results.json",
        ContentFile(
            bytes(json.dumps(detection, ensure_ascii=True, indent=2), "utf-8")
        ),
    )

    algorithms_job.outputs.add(civ)


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
        answer_type=Question.AnswerType.SINGLE_LINE_TEXT,
    )

    display_set = DisplaySet.objects.create(reader_study=reader_study)
    image = Image(
        name="test_image2.mha",
        modality=ImagingModality.objects.get(modality="MR"),
        width=128,
        height=128,
        color_space="RGB",
    )
    image.save()
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

    image = Image(
        name="test_image2.mha",
        modality=ImagingModality.objects.get(modality="MR"),
        width=128,
        height=128,
        color_space="RGB",
    )
    image.save()
    item = ArchiveItem.objects.create(archive=archive)
    civ = ComponentInterfaceValue.objects.create(
        interface=ComponentInterface.objects.get(slug="generic-medical-image"),
        image=image,
    )
    item.values.add(civ)


def _create_user_tokens(users):
    # Hard code tokens used in gcapi integration tests
    user_tokens = {
        "admin": "1b9436200001f2eaf57cd77db075cbb60a49a00a",
        "retina": "f1f98a1733c05b12118785ffd995c250fe4d90da",
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


def _set_statistics_cache():
    stats = {
        "users": [
            {
                "date_joined__year": 2012,
                "date_joined__month": 9,
                "object_count": 4,
            },
            {
                "date_joined__year": 2012,
                "date_joined__month": 10,
                "object_count": 2,
            },
            {
                "date_joined__year": 2012,
                "date_joined__month": 11,
                "object_count": 4,
            },
            {
                "date_joined__year": 2012,
                "date_joined__month": 12,
                "object_count": 1,
            },
            {
                "date_joined__year": 2013,
                "date_joined__month": 1,
                "object_count": 1,
            },
            {
                "date_joined__year": 2013,
                "date_joined__month": 2,
                "object_count": 1,
            },
            {
                "date_joined__year": 2013,
                "date_joined__month": 4,
                "object_count": 1,
            },
            {
                "date_joined__year": 2013,
                "date_joined__month": 5,
                "object_count": 1,
            },
            {
                "date_joined__year": 2013,
                "date_joined__month": 6,
                "object_count": 1,
            },
            {
                "date_joined__year": 2013,
                "date_joined__month": 10,
                "object_count": 5,
            },
            {
                "date_joined__year": 2013,
                "date_joined__month": 11,
                "object_count": 2,
            },
            {
                "date_joined__year": 2013,
                "date_joined__month": 12,
                "object_count": 32,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 1,
                "object_count": 47,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 2,
                "object_count": 41,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 3,
                "object_count": 104,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 4,
                "object_count": 46,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 5,
                "object_count": 58,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 6,
                "object_count": 34,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 7,
                "object_count": 41,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 8,
                "object_count": 21,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 9,
                "object_count": 35,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 10,
                "object_count": 26,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 11,
                "object_count": 38,
            },
            {
                "date_joined__year": 2014,
                "date_joined__month": 12,
                "object_count": 39,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 1,
                "object_count": 35,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 2,
                "object_count": 34,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 3,
                "object_count": 43,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 4,
                "object_count": 31,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 5,
                "object_count": 26,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 6,
                "object_count": 30,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 7,
                "object_count": 57,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 8,
                "object_count": 40,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 9,
                "object_count": 40,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 10,
                "object_count": 51,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 11,
                "object_count": 53,
            },
            {
                "date_joined__year": 2015,
                "date_joined__month": 12,
                "object_count": 101,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 1,
                "object_count": 142,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 2,
                "object_count": 114,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 3,
                "object_count": 108,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 4,
                "object_count": 112,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 5,
                "object_count": 67,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 6,
                "object_count": 74,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 7,
                "object_count": 106,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 8,
                "object_count": 100,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 9,
                "object_count": 136,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 10,
                "object_count": 166,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 11,
                "object_count": 192,
            },
            {
                "date_joined__year": 2016,
                "date_joined__month": 12,
                "object_count": 230,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 1,
                "object_count": 721,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 2,
                "object_count": 702,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 3,
                "object_count": 875,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 4,
                "object_count": 578,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 5,
                "object_count": 536,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 6,
                "object_count": 438,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 7,
                "object_count": 457,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 8,
                "object_count": 397,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 9,
                "object_count": 398,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 10,
                "object_count": 504,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 11,
                "object_count": 710,
            },
            {
                "date_joined__year": 2017,
                "date_joined__month": 12,
                "object_count": 624,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 1,
                "object_count": 733,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 2,
                "object_count": 560,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 3,
                "object_count": 784,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 4,
                "object_count": 771,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 5,
                "object_count": 784,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 6,
                "object_count": 769,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 7,
                "object_count": 838,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 8,
                "object_count": 735,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 9,
                "object_count": 708,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 10,
                "object_count": 958,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 11,
                "object_count": 1080,
            },
            {
                "date_joined__year": 2018,
                "date_joined__month": 12,
                "object_count": 792,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 1,
                "object_count": 1146,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 2,
                "object_count": 1014,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 3,
                "object_count": 1303,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 4,
                "object_count": 1218,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 5,
                "object_count": 1366,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 6,
                "object_count": 1237,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 7,
                "object_count": 1544,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 8,
                "object_count": 1245,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 9,
                "object_count": 1256,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 10,
                "object_count": 1370,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 11,
                "object_count": 1545,
            },
            {
                "date_joined__year": 2019,
                "date_joined__month": 12,
                "object_count": 1450,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 1,
                "object_count": 1325,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 2,
                "object_count": 1219,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 3,
                "object_count": 1046,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 4,
                "object_count": 1275,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 5,
                "object_count": 1231,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 6,
                "object_count": 1142,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 7,
                "object_count": 1103,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 8,
                "object_count": 915,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 9,
                "object_count": 980,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 10,
                "object_count": 1071,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 11,
                "object_count": 1460,
            },
            {
                "date_joined__year": 2020,
                "date_joined__month": 12,
                "object_count": 1108,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 1,
                "object_count": 1010,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 2,
                "object_count": 934,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 3,
                "object_count": 1163,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 4,
                "object_count": 1187,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 5,
                "object_count": 1122,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 6,
                "object_count": 998,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 7,
                "object_count": 1019,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 8,
                "object_count": 818,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 9,
                "object_count": 1028,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 10,
                "object_count": 1122,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 11,
                "object_count": 1076,
            },
            {
                "date_joined__year": 2021,
                "date_joined__month": 12,
                "object_count": 1054,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 1,
                "object_count": 1076,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 2,
                "object_count": 1133,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 3,
                "object_count": 1591,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 4,
                "object_count": 1561,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 5,
                "object_count": 1575,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 6,
                "object_count": 1387,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 7,
                "object_count": 1390,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 8,
                "object_count": 1063,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 9,
                "object_count": 1091,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 10,
                "object_count": 1309,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 11,
                "object_count": 1200,
            },
            {
                "date_joined__year": 2022,
                "date_joined__month": 12,
                "object_count": 960,
            },
            {
                "date_joined__year": 2023,
                "date_joined__month": 1,
                "object_count": 903,
            },
            {
                "date_joined__year": 2023,
                "date_joined__month": 2,
                "object_count": 1259,
            },
        ],
        "countries": [
            ("CN", 20105),
            ("US", 6097),
            ("IN", 5361),
            ("NL", 1783),
            ("DE", 1777),
            ("GB", 1723),
            ("KR", 1695),
            ("FR", 1128),
            ("CA", 1070),
            ("TW", 941),
            ("TR", 802),
            ("IR", 790),
            ("JP", 767),
            ("PK", 688),
            ("ES", 656),
            ("AU", 648),
            ("HK", 524),
            ("IT", 500),
            ("RU", 489),
            ("BR", 471),
            ("SG", 419),
            ("EG", 399),
            ("VN", 391),
            ("CH", 361),
            ("PL", 354),
            ("IL", 349),
            ("BD", 323),
            ("CO", 282),
            ("ID", 277),
            ("BE", 245),
            ("PT", 241),
            ("SE", 219),
            ("AT", 206),
            ("MX", 198),
            ("MY", 190),
            ("DZ", 183),
            ("AF", 159),
            ("GR", 153),
            ("DK", 149),
            ("MA", 146),
            ("TH", 135),
            ("TN", 124),
            ("AE", 122),
            ("RO", 119),
            ("NO", 116),
            ("IE", 112),
            ("SA", 110),
            ("FI", 102),
            ("HU", 95),
            ("CZ", 88),
            ("LK", 86),
            ("IQ", 82),
            ("UA", 81),
            ("AR", 80),
            ("CL", 69),
            ("SK", 63),
            ("NG", 62),
            ("BY", 59),
            ("PE", 59),
            ("ET", 59),
            ("NP", 57),
            ("ZA", 56),
            ("NZ", 56),
            ("AS", 50),
            ("PH", 50),
            ("JO", 49),
            ("AM", 47),
            ("KE", 45),
            ("KZ", 44),
            ("AX", 41),
            ("MO", 37),
            ("AL", 34),
            ("QA", 33),
            ("LT", 31),
            ("EC", 29),
            ("SI", 27),
            ("BS", 26),
            ("RS", 26),
            ("GH", 25),
            ("BH", 23),
            ("HR", 23),
            ("SY", 21),
            ("AO", 20),
            ("UG", 20),
            ("CM", 19),
            ("AZ", 18),
            ("CU", 17),
            ("AW", 17),
            ("EE", 16),
            ("ZW", 16),
            ("TZ", 16),
            ("CY", 14),
            ("MU", 13),
            ("IS", 13),
            ("LU", 12),
            ("PS", 12),
            ("SD", 12),
            ("BG", 12),
            ("AQ", 12),
            ("LB", 11),
            ("YE", 11),
            ("KP", 11),
            ("GE", 11),
            ("SN", 11),
            ("AD", 10),
            ("VE", 9),
            ("OM", 8),
            ("CX", 8),
            ("ZM", 8),
            ("AI", 8),
            ("LY", 8),
            ("CC", 7),
            ("BB", 7),
            ("MM", 7),
            ("HT", 7),
            ("MK", 6),
            ("RW", 6),
            ("CR", 6),
            ("BO", 6),
            ("KH", 6),
            ("MT", 6),
            ("SS", 6),
            ("LV", 6),
            ("KG", 5),
            ("KW", 5),
            ("MZ", 5),
            ("NA", 5),
            ("NF", 5),
            ("CI", 5),
            ("UY", 5),
            ("UZ", 5),
            ("AG", 5),
            ("BN", 4),
            ("BF", 4),
            ("VU", 4),
            ("GT", 4),
            ("TD", 4),
            ("UM", 4),
            ("ME", 4),
            ("PR", 4),
            ("BJ", 4),
            ("CG", 4),
            ("GM", 4),
            ("MN", 3),
            ("BT", 3),
            ("BW", 3),
            ("CV", 3),
            ("JM", 3),
            ("DO", 3),
            ("DM", 3),
            ("VI", 3),
            ("PY", 3),
            ("KM", 3),
            ("GQ", 3),
            ("WS", 3),
            ("TL", 3),
            ("TG", 3),
            ("MG", 3),
            ("HM", 2),
            ("WF", 2),
            ("NU", 2),
            ("PA", 2),
            ("EH", 2),
            ("PW", 2),
            ("DJ", 2),
            ("HN", 2),
            ("BA", 2),
            ("CD", 2),
            ("BZ", 2),
            ("SO", 2),
            ("IM", 2),
            ("SV", 2),
            ("TK", 2),
            ("KY", 2),
            ("BM", 2),
            ("BL", 2),
            ("BI", 2),
            ("IO", 2),
            ("MD", 2),
            ("GS", 1),
            ("SX", 1),
            ("FO", 1),
            ("SZ", 1),
            ("TC", 1),
            ("GA", 1),
            ("NR", 1),
            ("BQ", 1),
            ("GU", 1),
            ("GG", 1),
            ("GY", 1),
            ("TO", 1),
            ("GI", 1),
            ("TT", 1),
            ("MF", 1),
            ("MR", 1),
            ("GN", 1),
            ("MH", 1),
            ("NE", 1),
            ("GP", 1),
            ("LS", 1),
            ("PM", 1),
            ("MW", 1),
            ("LI", 1),
            ("KI", 1),
            ("FJ", 1),
            ("CF", 1),
            ("VA", 1),
            ("LA", 1),
            ("VC", 1),
            ("FM", 1),
            ("MC", 1),
            ("MV", 1),
            ("ST", 1),
        ],
        "challenges": [
            {
                "hidden": False,
                "created__year": 2010,
                "created__month": 5,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2013,
                "created__month": 9,
                "object_count": 5,
            },
            {
                "hidden": True,
                "created__year": 2013,
                "created__month": 9,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2013,
                "created__month": 10,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2013,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2014,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2014,
                "created__month": 2,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2014,
                "created__month": 5,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2014,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2015,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2015,
                "created__month": 4,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2015,
                "created__month": 5,
                "object_count": 4,
            },
            {
                "hidden": False,
                "created__year": 2015,
                "created__month": 10,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2015,
                "created__month": 10,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2016,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2016,
                "created__month": 1,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2016,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2016,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2017,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2017,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2017,
                "created__month": 4,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2017,
                "created__month": 4,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2017,
                "created__month": 5,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2017,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2017,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2017,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2017,
                "created__month": 10,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2017,
                "created__month": 10,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2017,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2017,
                "created__month": 12,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 1,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 2,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 2,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 3,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 3,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 4,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 5,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 5,
                "object_count": 5,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 7,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 8,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 9,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 9,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 10,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 10,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 11,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 11,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2018,
                "created__month": 12,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2018,
                "created__month": 12,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 1,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 2,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 2,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 3,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 4,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 4,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 5,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 5,
                "object_count": 5,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 7,
                "object_count": 4,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 8,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 8,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 9,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 9,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 10,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 10,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 11,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 11,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2019,
                "created__month": 12,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2019,
                "created__month": 12,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 1,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 1,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 2,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 2,
                "object_count": 10,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 3,
                "object_count": 5,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 4,
                "object_count": 7,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 4,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 5,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 6,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 8,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 9,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 9,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 10,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 10,
                "object_count": 4,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 11,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2020,
                "created__month": 12,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2020,
                "created__month": 12,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 1,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 2,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 2,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 3,
                "object_count": 11,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 3,
                "object_count": 4,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 4,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 4,
                "object_count": 8,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 5,
                "object_count": 5,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 7,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 8,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 9,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 9,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 10,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 10,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 11,
                "object_count": 5,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 11,
                "object_count": 6,
            },
            {
                "hidden": False,
                "created__year": 2021,
                "created__month": 12,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2021,
                "created__month": 12,
                "object_count": 8,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 1,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2022,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 2,
                "object_count": 4,
            },
            {
                "hidden": True,
                "created__year": 2022,
                "created__month": 2,
                "object_count": 4,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 3,
                "object_count": 8,
            },
            {
                "hidden": True,
                "created__year": 2022,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 4,
                "object_count": 8,
            },
            {
                "hidden": True,
                "created__year": 2022,
                "created__month": 4,
                "object_count": 3,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 5,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 3,
            },
            {
                "hidden": True,
                "created__year": 2022,
                "created__month": 8,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 2,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 10,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "hidden": True,
                "created__year": 2022,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "hidden": False,
                "created__year": 2022,
                "created__month": 12,
                "object_count": 2,
            },
            {
                "hidden": True,
                "created__year": 2023,
                "created__month": 1,
                "object_count": 2,
            },
        ],
        "submissions": [
            {
                "phase__submission_kind": 1,
                "created__year": 2017,
                "created__month": 12,
                "object_count": 2,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 1,
                "object_count": 2,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 2,
                "object_count": 277,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 3,
                "object_count": 560,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 4,
                "object_count": 208,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 5,
                "object_count": 122,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 6,
                "object_count": 130,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 7,
                "object_count": 122,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 8,
                "object_count": 196,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 9,
                "object_count": 143,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 10,
                "object_count": 170,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 11,
                "object_count": 383,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2018,
                "created__month": 12,
                "object_count": 251,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 1,
                "object_count": 430,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 2,
                "object_count": 1414,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 3,
                "object_count": 3700,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 4,
                "object_count": 450,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 5,
                "object_count": 713,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 6,
                "object_count": 898,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 7,
                "object_count": 1549,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 8,
                "object_count": 2800,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 9,
                "object_count": 4128,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 10,
                "object_count": 1386,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 11,
                "object_count": 1626,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2019,
                "created__month": 12,
                "object_count": 569,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 1,
                "object_count": 604,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 2,
                "object_count": 1883,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 3,
                "object_count": 1889,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 4,
                "object_count": 985,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 5,
                "object_count": 980,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 6,
                "object_count": 1306,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 7,
                "object_count": 3030,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 8,
                "object_count": 4480,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2020,
                "created__month": 8,
                "object_count": 1,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 9,
                "object_count": 1572,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 10,
                "object_count": 429,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2020,
                "created__month": 10,
                "object_count": 1,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 11,
                "object_count": 1713,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2020,
                "created__month": 12,
                "object_count": 1490,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 1,
                "object_count": 1281,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 2,
                "object_count": 2625,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2021,
                "created__month": 2,
                "object_count": 5,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 3,
                "object_count": 1677,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 4,
                "object_count": 805,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 5,
                "object_count": 572,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 1161,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 7,
                "object_count": 1774,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2021,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 8,
                "object_count": 1504,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2021,
                "created__month": 8,
                "object_count": 196,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 9,
                "object_count": 1858,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2021,
                "created__month": 9,
                "object_count": 79,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 10,
                "object_count": 1094,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2021,
                "created__month": 10,
                "object_count": 22,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 11,
                "object_count": 846,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2021,
                "created__month": 11,
                "object_count": 28,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2021,
                "created__month": 12,
                "object_count": 726,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2021,
                "created__month": 12,
                "object_count": 131,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 1,
                "object_count": 542,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 1,
                "object_count": 255,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 2,
                "object_count": 769,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 2,
                "object_count": 591,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 3,
                "object_count": 743,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 3,
                "object_count": 336,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 4,
                "object_count": 711,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 4,
                "object_count": 215,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 5,
                "object_count": 1376,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 5,
                "object_count": 183,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 2089,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 222,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 7,
                "object_count": 5816,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 7,
                "object_count": 284,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 8,
                "object_count": 3180,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 8,
                "object_count": 723,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 2259,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 521,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 10,
                "object_count": 1637,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 10,
                "object_count": 126,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 11,
                "object_count": 804,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 11,
                "object_count": 270,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2022,
                "created__month": 12,
                "object_count": 678,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2022,
                "created__month": 12,
                "object_count": 34,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2023,
                "created__month": 1,
                "object_count": 658,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2023,
                "created__month": 1,
                "object_count": 66,
            },
            {
                "phase__submission_kind": 1,
                "created__year": 2023,
                "created__month": 2,
                "object_count": 1110,
            },
            {
                "phase__submission_kind": 3,
                "created__year": 2023,
                "created__month": 2,
                "object_count": 165,
            },
        ],
        "algorithms": [
            {
                "public": False,
                "created__year": 2019,
                "created__month": 10,
                "object_count": 5,
            },
            {
                "public": True,
                "created__year": 2019,
                "created__month": 10,
                "object_count": 7,
            },
            {
                "public": False,
                "created__year": 2019,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2019,
                "created__month": 12,
                "object_count": 3,
            },
            {
                "public": True,
                "created__year": 2019,
                "created__month": 12,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 1,
                "object_count": 3,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 2,
                "object_count": 4,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 2,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 3,
                "object_count": 2,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 4,
                "object_count": 4,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 4,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 5,
                "object_count": 1,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 5,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 6,
                "object_count": 2,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 8,
                "object_count": 2,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 9,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 10,
                "object_count": 4,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 10,
                "object_count": 2,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 12,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 2,
                "object_count": 4,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 2,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 3,
                "object_count": 3,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 3,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 4,
                "object_count": 8,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 4,
                "object_count": 3,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 5,
                "object_count": 4,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 5,
                "object_count": 3,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 5,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 7,
                "object_count": 6,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 7,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 8,
                "object_count": 124,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 8,
                "object_count": 3,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 9,
                "object_count": 44,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 9,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 10,
                "object_count": 13,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 10,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 11,
                "object_count": 16,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 11,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 12,
                "object_count": 36,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 12,
                "object_count": 7,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 1,
                "object_count": 73,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 1,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 2,
                "object_count": 292,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 2,
                "object_count": 7,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 3,
                "object_count": 143,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 3,
                "object_count": 5,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 4,
                "object_count": 54,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 5,
                "object_count": 34,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 5,
                "object_count": 7,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 31,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 8,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 7,
                "object_count": 135,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 7,
                "object_count": 3,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 8,
                "object_count": 443,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 8,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 375,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 10,
                "object_count": 75,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 10,
                "object_count": 8,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 11,
                "object_count": 180,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 12,
                "object_count": 28,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 12,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2023,
                "created__month": 1,
                "object_count": 59,
            },
            {
                "public": False,
                "created__year": 2023,
                "created__month": 2,
                "object_count": 201,
            },
            {
                "public": True,
                "created__year": 2023,
                "created__month": 2,
                "object_count": 1,
            },
        ],
        "jobs": [
            {
                "created__year": 2018,
                "created__month": 11,
                "object_count": 4,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 2,
                "object_count": 13,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 3,
                "object_count": 5,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 4,
                "object_count": 13,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 5,
                "object_count": 11,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 6,
                "object_count": 3,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 7,
                "object_count": 9,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 8,
                "object_count": 2,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 9,
                "object_count": 1,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 10,
                "object_count": 17,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 11,
                "object_count": 19,
                "duration_sum": None,
            },
            {
                "created__year": 2019,
                "created__month": 12,
                "object_count": 96,
                "duration_sum": None,
            },
            {
                "created__year": 2020,
                "created__month": 1,
                "object_count": 44,
                "duration_sum": None,
            },
            {
                "created__year": 2020,
                "created__month": 2,
                "object_count": 105,
                "duration_sum": timedelta(seconds=1179, microseconds=759658),
            },
            {
                "created__year": 2020,
                "created__month": 3,
                "object_count": 66,
                "duration_sum": timedelta(seconds=19545, microseconds=808182),
            },
            {
                "created__year": 2020,
                "created__month": 4,
                "object_count": 1018,
                "duration_sum": timedelta(
                    days=6, seconds=49536, microseconds=662881
                ),
            },
            {
                "created__year": 2020,
                "created__month": 5,
                "object_count": 2387,
                "duration_sum": timedelta(
                    days=4, seconds=39884, microseconds=43556
                ),
            },
            {
                "created__year": 2020,
                "created__month": 6,
                "object_count": 537,
                "duration_sum": timedelta(
                    days=1, seconds=6868, microseconds=479246
                ),
            },
            {
                "created__year": 2020,
                "created__month": 7,
                "object_count": 96,
                "duration_sum": timedelta(seconds=65866, microseconds=443267),
            },
            {
                "created__year": 2020,
                "created__month": 8,
                "object_count": 936,
                "duration_sum": timedelta(seconds=54429, microseconds=560964),
            },
            {
                "created__year": 2020,
                "created__month": 9,
                "object_count": 735,
                "duration_sum": timedelta(
                    days=1, seconds=38288, microseconds=382901
                ),
            },
            {
                "created__year": 2020,
                "created__month": 10,
                "object_count": 509,
                "duration_sum": timedelta(
                    days=3, seconds=24106, microseconds=187032
                ),
            },
            {
                "created__year": 2020,
                "created__month": 11,
                "object_count": 2307,
                "duration_sum": timedelta(
                    days=4, seconds=30072, microseconds=653603
                ),
            },
            {
                "created__year": 2020,
                "created__month": 12,
                "object_count": 600,
                "duration_sum": timedelta(seconds=60592, microseconds=940863),
            },
            {
                "created__year": 2021,
                "created__month": 1,
                "object_count": 404,
                "duration_sum": timedelta(
                    days=1, seconds=48914, microseconds=453527
                ),
            },
            {
                "created__year": 2021,
                "created__month": 2,
                "object_count": 4768,
                "duration_sum": timedelta(
                    days=9, seconds=7732, microseconds=427103
                ),
            },
            {
                "created__year": 2021,
                "created__month": 3,
                "object_count": 1774,
                "duration_sum": timedelta(
                    days=12, seconds=24346, microseconds=246879
                ),
            },
            {
                "created__year": 2021,
                "created__month": 4,
                "object_count": 5762,
                "duration_sum": timedelta(
                    days=227, seconds=7462, microseconds=153157
                ),
            },
            {
                "created__year": 2021,
                "created__month": 5,
                "object_count": 3347,
                "duration_sum": timedelta(
                    days=7, seconds=6450, microseconds=418644
                ),
            },
            {
                "created__year": 2021,
                "created__month": 6,
                "object_count": 5565,
                "duration_sum": timedelta(
                    days=24, seconds=83837, microseconds=160722
                ),
            },
            {
                "created__year": 2021,
                "created__month": 7,
                "object_count": 5495,
                "duration_sum": timedelta(
                    days=18, seconds=75234, microseconds=172042
                ),
            },
            {
                "created__year": 2021,
                "created__month": 8,
                "object_count": 5337,
                "duration_sum": timedelta(
                    days=14, seconds=67022, microseconds=366891
                ),
            },
            {
                "created__year": 2021,
                "created__month": 9,
                "object_count": 7823,
                "duration_sum": timedelta(
                    days=143, seconds=75929, microseconds=483935
                ),
            },
            {
                "created__year": 2021,
                "created__month": 10,
                "object_count": 7404,
                "duration_sum": timedelta(
                    days=77, seconds=9690, microseconds=584980
                ),
            },
            {
                "created__year": 2021,
                "created__month": 11,
                "object_count": 399,
                "duration_sum": timedelta(
                    days=27, seconds=36876, microseconds=689138
                ),
            },
            {
                "created__year": 2021,
                "created__month": 12,
                "object_count": 5520,
                "duration_sum": timedelta(
                    days=6, seconds=86319, microseconds=604256
                ),
            },
            {
                "created__year": 2022,
                "created__month": 1,
                "object_count": 23105,
                "duration_sum": timedelta(
                    days=23, seconds=24137, microseconds=14299
                ),
            },
            {
                "created__year": 2022,
                "created__month": 2,
                "object_count": 8894,
                "duration_sum": timedelta(
                    days=18, seconds=55472, microseconds=796510
                ),
            },
            {
                "created__year": 2022,
                "created__month": 3,
                "object_count": 30942,
                "duration_sum": timedelta(
                    days=62, seconds=41930, microseconds=868111
                ),
            },
            {
                "created__year": 2022,
                "created__month": 4,
                "object_count": 31789,
                "duration_sum": timedelta(
                    days=85, seconds=23206, microseconds=650211
                ),
            },
            {
                "created__year": 2022,
                "created__month": 5,
                "object_count": 15871,
                "duration_sum": timedelta(
                    days=356, seconds=15666, microseconds=674202
                ),
            },
            {
                "created__year": 2022,
                "created__month": 6,
                "object_count": 28062,
                "duration_sum": timedelta(
                    days=447, seconds=66891, microseconds=252144
                ),
            },
            {
                "created__year": 2022,
                "created__month": 7,
                "object_count": 19523,
                "duration_sum": timedelta(
                    days=52, seconds=68934, microseconds=809203
                ),
            },
            {
                "created__year": 2022,
                "created__month": 8,
                "object_count": 29357,
                "duration_sum": timedelta(
                    days=99, seconds=53272, microseconds=23620
                ),
            },
            {
                "created__year": 2022,
                "created__month": 9,
                "object_count": 39006,
                "duration_sum": timedelta(days=157, seconds=54972),
            },
            {
                "created__year": 2022,
                "created__month": 10,
                "object_count": 23286,
                "duration_sum": timedelta(days=104, seconds=9086),
            },
            {
                "created__year": 2022,
                "created__month": 11,
                "object_count": 57522,
                "duration_sum": timedelta(days=231, seconds=6164),
            },
            {
                "created__year": 2022,
                "created__month": 12,
                "object_count": 27913,
                "duration_sum": timedelta(days=122, seconds=72498),
            },
            {
                "created__year": 2023,
                "created__month": 1,
                "object_count": 17115,
                "duration_sum": timedelta(days=48, seconds=68862),
            },
            {
                "created__year": 2023,
                "created__month": 2,
                "object_count": 40318,
                "duration_sum": timedelta(days=71, seconds=17380),
            },
        ],
        "archives": [
            {
                "public": False,
                "created__year": 2019,
                "created__month": 2,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2019,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2019,
                "created__month": 8,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2019,
                "created__month": 10,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2019,
                "created__month": 12,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 3,
                "object_count": 3,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 4,
                "object_count": 8,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 5,
                "object_count": 2,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 5,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 6,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 8,
                "object_count": 10,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 9,
                "object_count": 2,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 9,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 10,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 12,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 1,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 2,
                "object_count": 5,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 3,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 4,
                "object_count": 8,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 4,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 5,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 7,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 7,
                "object_count": 5,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 8,
                "object_count": 6,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 8,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 9,
                "object_count": 15,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 10,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 11,
                "object_count": 3,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 12,
                "object_count": 12,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 1,
                "object_count": 9,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 2,
                "object_count": 9,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 3,
                "object_count": 9,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 4,
                "object_count": 6,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 5,
                "object_count": 13,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 18,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 7,
                "object_count": 12,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 8,
                "object_count": 6,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 6,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 11,
                "object_count": 19,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 12,
                "object_count": 69,
            },
            {
                "public": False,
                "created__year": 2023,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "public": True,
                "created__year": 2023,
                "created__month": 1,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2023,
                "created__month": 2,
                "object_count": 9,
            },
        ],
        "images": [
            {"created__year": 2018, "created__month": 8, "object_count": 140},
            {"created__year": 2018, "created__month": 9, "object_count": 774},
            {"created__year": 2018, "created__month": 11, "object_count": 2},
            {"created__year": 2019, "created__month": 2, "object_count": 679},
            {"created__year": 2019, "created__month": 3, "object_count": 733},
            {"created__year": 2019, "created__month": 4, "object_count": 26},
            {"created__year": 2019, "created__month": 5, "object_count": 569},
            {"created__year": 2019, "created__month": 6, "object_count": 4},
            {"created__year": 2019, "created__month": 7, "object_count": 15},
            {"created__year": 2019, "created__month": 8, "object_count": 3357},
            {
                "created__year": 2019,
                "created__month": 9,
                "object_count": 16073,
            },
            {"created__year": 2019, "created__month": 10, "object_count": 980},
            {"created__year": 2019, "created__month": 11, "object_count": 222},
            {
                "created__year": 2019,
                "created__month": 12,
                "object_count": 2252,
            },
            {"created__year": 2020, "created__month": 1, "object_count": 836},
            {"created__year": 2020, "created__month": 2, "object_count": 3317},
            {"created__year": 2020, "created__month": 3, "object_count": 7950},
            {"created__year": 2020, "created__month": 4, "object_count": 7381},
            {"created__year": 2020, "created__month": 5, "object_count": 4982},
            {"created__year": 2020, "created__month": 6, "object_count": 2419},
            {"created__year": 2020, "created__month": 7, "object_count": 1027},
            {"created__year": 2020, "created__month": 8, "object_count": 1294},
            {"created__year": 2020, "created__month": 9, "object_count": 1915},
            {
                "created__year": 2020,
                "created__month": 10,
                "object_count": 3575,
            },
            {
                "created__year": 2020,
                "created__month": 11,
                "object_count": 6846,
            },
            {
                "created__year": 2020,
                "created__month": 12,
                "object_count": 5767,
            },
            {"created__year": 2021, "created__month": 1, "object_count": 5291},
            {
                "created__year": 2021,
                "created__month": 2,
                "object_count": 10610,
            },
            {
                "created__year": 2021,
                "created__month": 3,
                "object_count": 30243,
            },
            {
                "created__year": 2021,
                "created__month": 4,
                "object_count": 14162,
            },
            {
                "created__year": 2021,
                "created__month": 5,
                "object_count": 13796,
            },
            {
                "created__year": 2021,
                "created__month": 6,
                "object_count": 21762,
            },
            {"created__year": 2021, "created__month": 7, "object_count": 9939},
            {"created__year": 2021, "created__month": 8, "object_count": 5902},
            {
                "created__year": 2021,
                "created__month": 9,
                "object_count": 18763,
            },
            {
                "created__year": 2021,
                "created__month": 10,
                "object_count": 18334,
            },
            {
                "created__year": 2021,
                "created__month": 11,
                "object_count": 2879,
            },
            {
                "created__year": 2021,
                "created__month": 12,
                "object_count": 15878,
            },
            {"created__year": 2022, "created__month": 1, "object_count": 5764},
            {"created__year": 2022, "created__month": 2, "object_count": 6397},
            {
                "created__year": 2022,
                "created__month": 3,
                "object_count": 42945,
            },
            {
                "created__year": 2022,
                "created__month": 4,
                "object_count": 14889,
            },
            {
                "created__year": 2022,
                "created__month": 5,
                "object_count": 28000,
            },
            {
                "created__year": 2022,
                "created__month": 6,
                "object_count": 35343,
            },
            {
                "created__year": 2022,
                "created__month": 7,
                "object_count": 16903,
            },
            {
                "created__year": 2022,
                "created__month": 8,
                "object_count": 27579,
            },
            {
                "created__year": 2022,
                "created__month": 9,
                "object_count": 29606,
            },
            {
                "created__year": 2022,
                "created__month": 10,
                "object_count": 41571,
            },
            {
                "created__year": 2022,
                "created__month": 11,
                "object_count": 75357,
            },
            {
                "created__year": 2022,
                "created__month": 12,
                "object_count": 74049,
            },
            {
                "created__year": 2023,
                "created__month": 1,
                "object_count": 12313,
            },
            {
                "created__year": 2023,
                "created__month": 2,
                "object_count": 12306,
            },
        ],
        "reader_studies": [
            {
                "public": False,
                "created__year": 2019,
                "created__month": 8,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2019,
                "created__month": 10,
                "object_count": 5,
            },
            {
                "public": False,
                "created__year": 2019,
                "created__month": 11,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 1,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 2,
                "object_count": 7,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 3,
                "object_count": 14,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 4,
                "object_count": 14,
            },
            {
                "public": True,
                "created__year": 2020,
                "created__month": 4,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 5,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 6,
                "object_count": 6,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 7,
                "object_count": 5,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 8,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 9,
                "object_count": 11,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 10,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 11,
                "object_count": 6,
            },
            {
                "public": False,
                "created__year": 2020,
                "created__month": 12,
                "object_count": 4,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 1,
                "object_count": 15,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 2,
                "object_count": 22,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 3,
                "object_count": 16,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 4,
                "object_count": 11,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 5,
                "object_count": 16,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 30,
            },
            {
                "public": True,
                "created__year": 2021,
                "created__month": 6,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 7,
                "object_count": 9,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 8,
                "object_count": 11,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 9,
                "object_count": 26,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 10,
                "object_count": 10,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 11,
                "object_count": 6,
            },
            {
                "public": False,
                "created__year": 2021,
                "created__month": 12,
                "object_count": 5,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 1,
                "object_count": 6,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 2,
                "object_count": 16,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 3,
                "object_count": 18,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 4,
                "object_count": 7,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 4,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 5,
                "object_count": 12,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 17,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 6,
                "object_count": 2,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 7,
                "object_count": 19,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 8,
                "object_count": 13,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 21,
            },
            {
                "public": True,
                "created__year": 2022,
                "created__month": 9,
                "object_count": 1,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 10,
                "object_count": 10,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 11,
                "object_count": 11,
            },
            {
                "public": False,
                "created__year": 2022,
                "created__month": 12,
                "object_count": 9,
            },
            {
                "public": False,
                "created__year": 2023,
                "created__month": 1,
                "object_count": 5,
            },
            {
                "public": False,
                "created__year": 2023,
                "created__month": 2,
                "object_count": 8,
            },
        ],
        "answers": [
            {"created__year": 2019, "created__month": 10, "object_count": 815},
            {
                "created__year": 2019,
                "created__month": 11,
                "object_count": 1029,
            },
            {"created__year": 2019, "created__month": 12, "object_count": 395},
            {"created__year": 2020, "created__month": 1, "object_count": 2118},
            {
                "created__year": 2020,
                "created__month": 2,
                "object_count": 18568,
            },
            {
                "created__year": 2020,
                "created__month": 3,
                "object_count": 31196,
            },
            {
                "created__year": 2020,
                "created__month": 4,
                "object_count": 32519,
            },
            {"created__year": 2020, "created__month": 5, "object_count": 7610},
            {"created__year": 2020, "created__month": 6, "object_count": 3671},
            {"created__year": 2020, "created__month": 7, "object_count": 9555},
            {
                "created__year": 2020,
                "created__month": 8,
                "object_count": 12084,
            },
            {"created__year": 2020, "created__month": 9, "object_count": 5956},
            {
                "created__year": 2020,
                "created__month": 10,
                "object_count": 18972,
            },
            {
                "created__year": 2020,
                "created__month": 11,
                "object_count": 11019,
            },
            {
                "created__year": 2020,
                "created__month": 12,
                "object_count": 5401,
            },
            {"created__year": 2021, "created__month": 1, "object_count": 1704},
            {
                "created__year": 2021,
                "created__month": 2,
                "object_count": 11364,
            },
            {
                "created__year": 2021,
                "created__month": 3,
                "object_count": 16776,
            },
            {
                "created__year": 2021,
                "created__month": 4,
                "object_count": 28837,
            },
            {"created__year": 2021, "created__month": 5, "object_count": 5168},
            {"created__year": 2021, "created__month": 6, "object_count": 7940},
            {"created__year": 2021, "created__month": 7, "object_count": 6154},
            {
                "created__year": 2021,
                "created__month": 8,
                "object_count": 10228,
            },
            {
                "created__year": 2021,
                "created__month": 9,
                "object_count": 10171,
            },
            {
                "created__year": 2021,
                "created__month": 10,
                "object_count": 11499,
            },
            {
                "created__year": 2021,
                "created__month": 11,
                "object_count": 23669,
            },
            {
                "created__year": 2021,
                "created__month": 12,
                "object_count": 11341,
            },
            {
                "created__year": 2022,
                "created__month": 1,
                "object_count": 24434,
            },
            {
                "created__year": 2022,
                "created__month": 2,
                "object_count": 21222,
            },
            {
                "created__year": 2022,
                "created__month": 3,
                "object_count": 16873,
            },
            {"created__year": 2022, "created__month": 4, "object_count": 9228},
            {
                "created__year": 2022,
                "created__month": 5,
                "object_count": 16488,
            },
            {"created__year": 2022, "created__month": 6, "object_count": 8990},
            {
                "created__year": 2022,
                "created__month": 7,
                "object_count": 24985,
            },
            {
                "created__year": 2022,
                "created__month": 8,
                "object_count": 19421,
            },
            {
                "created__year": 2022,
                "created__month": 9,
                "object_count": 24088,
            },
            {
                "created__year": 2022,
                "created__month": 10,
                "object_count": 36822,
            },
            {
                "created__year": 2022,
                "created__month": 11,
                "object_count": 82554,
            },
            {
                "created__year": 2022,
                "created__month": 12,
                "object_count": 25536,
            },
            {
                "created__year": 2023,
                "created__month": 1,
                "object_count": 24040,
            },
            {
                "created__year": 2023,
                "created__month": 2,
                "object_count": 30314,
            },
        ],
        "sessions": [
            {
                "created__year": 2019,
                "created__month": 4,
                "duration_sum": timedelta(seconds=15000),
                "object_count": 25,
            },
            {
                "created__year": 2019,
                "created__month": 5,
                "duration_sum": timedelta(seconds=55800),
                "object_count": 93,
            },
            {
                "created__year": 2019,
                "created__month": 6,
                "duration_sum": timedelta(seconds=21000),
                "object_count": 35,
            },
            {
                "created__year": 2019,
                "created__month": 7,
                "duration_sum": timedelta(seconds=32400),
                "object_count": 54,
            },
            {
                "created__year": 2019,
                "created__month": 8,
                "duration_sum": timedelta(seconds=29400),
                "object_count": 49,
            },
            {
                "created__year": 2019,
                "created__month": 9,
                "duration_sum": timedelta(
                    days=1, seconds=52604, microseconds=391102
                ),
                "object_count": 86,
            },
            {
                "created__year": 2019,
                "created__month": 10,
                "duration_sum": timedelta(
                    days=2, seconds=33607, microseconds=830937
                ),
                "object_count": 116,
            },
            {
                "created__year": 2019,
                "created__month": 11,
                "duration_sum": timedelta(
                    days=4, seconds=11185, microseconds=489788
                ),
                "object_count": 141,
            },
            {
                "created__year": 2019,
                "created__month": 12,
                "duration_sum": timedelta(
                    days=1, seconds=81224, microseconds=424205
                ),
                "object_count": 113,
            },
            {
                "created__year": 2020,
                "created__month": 1,
                "duration_sum": timedelta(
                    days=3, seconds=81876, microseconds=602535
                ),
                "object_count": 209,
            },
            {
                "created__year": 2020,
                "created__month": 2,
                "duration_sum": timedelta(
                    days=7, seconds=49915, microseconds=273891
                ),
                "object_count": 353,
            },
            {
                "created__year": 2020,
                "created__month": 3,
                "duration_sum": timedelta(
                    days=17, seconds=20451, microseconds=157326
                ),
                "object_count": 513,
            },
            {
                "created__year": 2020,
                "created__month": 4,
                "duration_sum": timedelta(
                    days=24, seconds=61459, microseconds=875687
                ),
                "object_count": 801,
            },
            {
                "created__year": 2020,
                "created__month": 5,
                "duration_sum": timedelta(
                    days=15, seconds=55404, microseconds=30450
                ),
                "object_count": 759,
            },
            {
                "created__year": 2020,
                "created__month": 6,
                "duration_sum": timedelta(
                    days=10, seconds=18539, microseconds=315562
                ),
                "object_count": 466,
            },
            {
                "created__year": 2020,
                "created__month": 7,
                "duration_sum": timedelta(
                    days=11, seconds=57907, microseconds=942365
                ),
                "object_count": 346,
            },
            {
                "created__year": 2020,
                "created__month": 8,
                "duration_sum": timedelta(
                    days=14, seconds=18126, microseconds=40714
                ),
                "object_count": 469,
            },
            {
                "created__year": 2020,
                "created__month": 9,
                "duration_sum": timedelta(
                    days=15, seconds=68842, microseconds=304099
                ),
                "object_count": 495,
            },
            {
                "created__year": 2020,
                "created__month": 10,
                "duration_sum": timedelta(
                    days=27, seconds=64847, microseconds=328302
                ),
                "object_count": 727,
            },
            {
                "created__year": 2020,
                "created__month": 11,
                "duration_sum": timedelta(
                    days=19, seconds=12013, microseconds=811107
                ),
                "object_count": 615,
            },
            {
                "created__year": 2020,
                "created__month": 12,
                "duration_sum": timedelta(
                    days=10, seconds=71415, microseconds=872185
                ),
                "object_count": 364,
            },
            {
                "created__year": 2021,
                "created__month": 1,
                "duration_sum": timedelta(
                    days=12, seconds=3989, microseconds=902112
                ),
                "object_count": 460,
            },
            {
                "created__year": 2021,
                "created__month": 2,
                "duration_sum": timedelta(
                    days=25, seconds=60591, microseconds=637103
                ),
                "object_count": 777,
            },
            {
                "created__year": 2021,
                "created__month": 3,
                "duration_sum": timedelta(
                    days=26, seconds=23021, microseconds=694828
                ),
                "object_count": 819,
            },
            {
                "created__year": 2021,
                "created__month": 4,
                "duration_sum": timedelta(
                    days=19, seconds=65743, microseconds=821119
                ),
                "object_count": 740,
            },
            {
                "created__year": 2021,
                "created__month": 5,
                "duration_sum": timedelta(
                    days=19, seconds=36879, microseconds=218064
                ),
                "object_count": 684,
            },
            {
                "created__year": 2021,
                "created__month": 6,
                "duration_sum": timedelta(
                    days=23, seconds=50953, microseconds=160099
                ),
                "object_count": 825,
            },
            {
                "created__year": 2021,
                "created__month": 7,
                "duration_sum": timedelta(
                    days=15, seconds=52255, microseconds=46486
                ),
                "object_count": 517,
            },
            {
                "created__year": 2021,
                "created__month": 8,
                "duration_sum": timedelta(
                    days=15, seconds=75020, microseconds=710434
                ),
                "object_count": 672,
            },
            {
                "created__year": 2021,
                "created__month": 9,
                "duration_sum": timedelta(
                    days=23, seconds=25142, microseconds=56154
                ),
                "object_count": 870,
            },
            {
                "created__year": 2021,
                "created__month": 10,
                "duration_sum": timedelta(
                    days=26, seconds=47761, microseconds=589414
                ),
                "object_count": 794,
            },
            {
                "created__year": 2021,
                "created__month": 11,
                "duration_sum": timedelta(
                    days=22, seconds=9722, microseconds=255139
                ),
                "object_count": 709,
            },
            {
                "created__year": 2021,
                "created__month": 12,
                "duration_sum": timedelta(
                    days=13, seconds=29448, microseconds=468257
                ),
                "object_count": 403,
            },
            {
                "created__year": 2022,
                "created__month": 1,
                "duration_sum": timedelta(
                    days=13, seconds=31585, microseconds=368146
                ),
                "object_count": 484,
            },
            {
                "created__year": 2022,
                "created__month": 2,
                "duration_sum": timedelta(
                    days=33, seconds=85813, microseconds=713021
                ),
                "object_count": 1165,
            },
            {
                "created__year": 2022,
                "created__month": 3,
                "duration_sum": timedelta(
                    days=29, seconds=67850, microseconds=681807
                ),
                "object_count": 983,
            },
            {
                "created__year": 2022,
                "created__month": 4,
                "duration_sum": timedelta(
                    days=23, seconds=62733, microseconds=614976
                ),
                "object_count": 896,
            },
            {
                "created__year": 2022,
                "created__month": 5,
                "duration_sum": timedelta(
                    days=25, seconds=18807, microseconds=952580
                ),
                "object_count": 811,
            },
            {
                "created__year": 2022,
                "created__month": 6,
                "duration_sum": timedelta(
                    days=17, seconds=28453, microseconds=193329
                ),
                "object_count": 733,
            },
            {
                "created__year": 2022,
                "created__month": 7,
                "duration_sum": timedelta(
                    days=19, seconds=23204, microseconds=424114
                ),
                "object_count": 634,
            },
            {
                "created__year": 2022,
                "created__month": 8,
                "duration_sum": timedelta(
                    days=17, seconds=32713, microseconds=898836
                ),
                "object_count": 831,
            },
            {
                "created__year": 2022,
                "created__month": 9,
                "duration_sum": timedelta(
                    days=24, seconds=7818, microseconds=324048
                ),
                "object_count": 871,
            },
            {
                "created__year": 2022,
                "created__month": 10,
                "duration_sum": timedelta(
                    days=25, seconds=52587, microseconds=487901
                ),
                "object_count": 774,
            },
            {
                "created__year": 2022,
                "created__month": 11,
                "duration_sum": timedelta(
                    days=36, seconds=75746, microseconds=768441
                ),
                "object_count": 1058,
            },
            {
                "created__year": 2022,
                "created__month": 12,
                "duration_sum": timedelta(
                    days=27, seconds=17821, microseconds=316294
                ),
                "object_count": 754,
            },
            {
                "created__year": 2023,
                "created__month": 1,
                "duration_sum": timedelta(
                    days=22, seconds=8533, microseconds=294954
                ),
                "object_count": 618,
            },
            {
                "created__year": 2023,
                "created__month": 2,
                "duration_sum": timedelta(
                    days=31, seconds=81341, microseconds=216401
                ),
                "object_count": 1073,
            },
        ],
    }

    cache.set(settings.STATISTICS_SITE_CACHE_KEY, stats, timeout=None)
