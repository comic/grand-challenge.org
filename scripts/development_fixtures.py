import base64
import json
import logging
import os
from datetime import timedelta

import boto3
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.core.files.base import ContentFile
from django.utils import timezone
from guardian.shortcuts import assign_perm
from knox import crypto
from knox.models import AuthToken
from knox.settings import CONSTANTS
from machina.apps.forum.models import Forum

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.anatomy.models import BodyRegion, BodyStructure
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
from grandchallenge.core.storage import public_s3_storage
from grandchallenge.evaluation.models import (
    Evaluation,
    Method,
    Phase,
    Submission,
)
from grandchallenge.github.models import GitHubUserToken, GitHubWebhookMessage
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.pages.models import Page
from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from grandchallenge.task_categories.models import TaskType
from grandchallenge.workstations.models import Workstation
from tests.fixtures import create_uploaded_image

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

    site = Site.objects.get(pk=settings.SITE_ID)
    if site.domain == "gc.localhost":
        raise RuntimeError("Fixtures already initialised")

    site.domain = "gc.localhost"
    site.name = "Grand Challenge"
    site.save()

    _create_flatpages(site)

    users = _create_users(usernames=DEFAULT_USERS)
    _set_user_permissions(users)
    _create_help_forum()
    _create_demo_challenge(users)
    _create_external_challenge(users)
    _create_workstation(users)
    _create_algorithm_demo(users)
    _create_reader_studies(users)
    _create_user_tokens(users)
    _create_github_user_token(users["algorithm"])
    _create_github_webhook_message()
    _setup_public_storage()

    print("✨ Development fixtures successfully created ✨")


def _create_flatpages(site):
    page = FlatPage.objects.create(
        url="/example-flatpage/",
        title="Example Flatpage",
        content="<p>You can add flatpages via django admin</p>",
    )
    page.sites.add(site)


def _create_users(usernames):
    users = {}

    for username in usernames:
        users[username] = get_user_model().objects.create(
            username=username, email=f"{username}@example.com", is_active=True,
        )
        users[username].set_password(username)
        users[username].save()

        EmailAddress.objects.create(
            user=users[username],
            email=users[username].email,
            verified=True,
            primary=True,
        )

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

    Page.objects.create(challenge=demo, title="all", permission_level="ALL")
    Page.objects.create(challenge=demo, title="reg", permission_level="REG")
    Page.objects.create(challenge=demo, title="adm", permission_level="ADM")

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
            phase.submission_kind = phase.SubmissionKind.ALGORITHM
        phase.evaluation_detail_observable_url = (
            phase.evaluation_comparison_observable_url
        ) = "https://observablehq.com/embed/@grand-challenge/data-fetch-example?cell=*"
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
            submission=submission, method=method, status=Evaluation.SUCCESS,
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

    if os.path.isfile(settings.DEMO_ALGORITHM_IMAGE_PATH):
        with open(settings.DEMO_ALGORITHM_IMAGE_PATH, "rb") as f:
            container = File(f)
            algorithm_image.image.save("test_algorithm.tar", container)
            algorithm_image.image_sha256 = settings.DEMO_ALGORITHM_SHA256
    else:
        container = ContentFile(base64.b64decode(b""))
        algorithm_image.image.save("test_algorithm.tar", container)

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
    for res, det in zip(results, detections):
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
        interface=ComponentInterface.objects.get(slug="detection-results"),
    )
    civ.file.save(
        "detection_results.json",
        ContentFile(
            bytes(json.dumps(detection, ensure_ascii=True, indent=2), "utf-8")
        ),
    )

    algorithms_job.outputs.add(civ)


def _create_workstation(users):
    w = Workstation.objects.create(
        title=settings.DEFAULT_WORKSTATION_SLUG,
        logo=create_uploaded_image(),
        public=True,
    )
    w.add_editor(user=users["workstation"])


def _create_reader_studies(users):
    reader_study = ReaderStudy.objects.create(
        title="Reader Study",
        workstation=Workstation.objects.last(),
        logo=create_uploaded_image(),
        description="Test reader study",
    )
    reader_study.editors_group.user_set.add(users["readerstudy"])
    reader_study.readers_group.user_set.add(users["demo"])

    question = Question.objects.create(
        reader_study=reader_study,
        question_text="foo",
        answer_type=Question.AnswerType.SINGLE_LINE_TEXT,
    )

    answer = Answer.objects.create(
        creator=users["readerstudy"], question=question, answer="foo"
    )
    answer.images.add(Image.objects.first())
    answer.save()


def _create_user_tokens(users):
    # Hard code tokens used in gcapi integration tests
    user_tokens = {
        "admin": "1b9436200001f2eaf57cd77db075cbb60a49a00a",
        "retina": "f1f98a1733c05b12118785ffd995c250fe4d90da",
        "readerstudy": "01614a77b1c0b4ecd402be50a8ff96188d5b011d",
        "demop": "00aa710f4dc5621a0cb64b0795fbba02e39d7700",
    }

    out = f"{'*' * 80}\n"
    for user, token in user_tokens.items():
        salt = crypto.create_salt_string()
        digest = crypto.hash_token(token, salt)

        AuthToken(
            token_key=token[: CONSTANTS.TOKEN_KEY_LENGTH],
            digest=digest,
            salt=salt,
            user=users[user],
            expiry=None,
        ).save()

        out += f"\t{user} token is: {token}\n"
    out += f"{'*' * 80}\n"
    logger.debug(out)


def _setup_public_storage():
    """
    Add anonymous read only to public S3 storage.

    Only used in development, in production, set a similar policy manually
    on the S3 bucket.
    """
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{public_s3_storage.bucket_name}/*",
            }
        ],
    }

    bucket_policy = json.dumps(bucket_policy)

    # Get or create the bucket
    _ = public_s3_storage.bucket

    s3 = boto3.client(
        "s3",
        aws_access_key_id=public_s3_storage.access_key,
        aws_secret_access_key=public_s3_storage.secret_key,
        aws_session_token=public_s3_storage.security_token,
        region_name=public_s3_storage.region_name,
        use_ssl=public_s3_storage.use_ssl,
        endpoint_url=public_s3_storage.endpoint_url,
        config=public_s3_storage.config,
        verify=public_s3_storage.verify,
    )

    s3.put_bucket_policy(
        Bucket=public_s3_storage.bucket_name, Policy=bucket_policy
    )
