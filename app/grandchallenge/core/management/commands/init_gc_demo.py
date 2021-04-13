import base64
import json
import logging
import os
from io import BytesIO

import boto3
from PIL import Image
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile, File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management import BaseCommand
from knox import crypto
from knox.models import AuthToken
from knox.settings import CONSTANTS

import grandchallenge.cases.models
from grandchallenge.algorithms.models import Algorithm, AlgorithmImage
from grandchallenge.anatomy.models import BodyRegion, BodyStructure
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
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.pages.models import Page
from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from grandchallenge.task_categories.models import TaskType
from grandchallenge.workspaces.models import (
    WorkspaceKindChoices,
    WorkspaceTypeConfiguration,
)
from grandchallenge.workstations.models import Workstation

logger = logging.getLogger(__name__)


def get_temporary_image():
    io = BytesIO()
    size = (200, 200)
    color = (255, 0, 0)
    image = Image.new("RGB", size, color)
    image.save(io, format="JPEG")
    image_file = InMemoryUploadedFile(
        io, None, "foo.jpg", "jpeg", image.size, None
    )
    image_file.seek(0)
    return image_file


class Command(BaseCommand):
    users = None

    def handle(self, *args, **options):
        """Creates the main project, demo user and demo challenge."""
        if not settings.DEBUG:
            raise RuntimeError(
                "Skipping this command, server is not in DEBUG mode."
            )

        # Set the default domain that is used in RequestFactory
        site = Site.objects.get(pk=settings.SITE_ID)
        if site.domain == "gc.localhost":
            # Already initialised
            return

        site.domain = "gc.localhost"
        site.name = "Grand Challenge"
        site.save()

        self._create_flatpages(site)

        default_users = [
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
        self.users = self._create_users(usernames=default_users)
        self.users[
            settings.RETINA_IMPORT_USER_NAME
        ] = get_user_model().objects.get(
            username=settings.RETINA_IMPORT_USER_NAME
        )

        self._set_user_permissions()
        self._create_demo_challenge()
        self._create_external_challenge()
        self._create_workstation()
        self._create_algorithm_demo()
        self._create_io_algorithm()
        self._create_reader_studies()
        self._create_user_tokens()
        self._setup_public_storage()

    @staticmethod
    def _create_flatpages(site):
        page = FlatPage.objects.create(
            url="/about/",
            title="About",
            content="<p>You can add flatpages via django admin</p>",
        )
        page.sites.add(site)

    @staticmethod
    def _create_users(usernames):
        users = {}

        for username in usernames:
            users[username] = get_user_model().objects.create(
                username=username,
                email=f"{username}@example.com",
                is_active=True,
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

    def _set_user_permissions(self):
        self.users["admin"].is_staff = True
        self.users["admin"].save()

        retina_group = Group.objects.get(
            name=settings.RETINA_GRADERS_GROUP_NAME
        )
        self.users["retina"].groups.add(retina_group)

        rs_group = Group.objects.get(
            name=settings.READER_STUDY_CREATORS_GROUP_NAME
        )
        self.users["readerstudy"].groups.add(rs_group)

        workstation_group = Group.objects.get(
            name=settings.WORKSTATIONS_CREATORS_GROUP_NAME
        )
        self.users["workstation"].groups.add(workstation_group)
        self.users["workstation"].user_permissions.add(
            Permission.objects.get(codename="add_workstationconfig")
        )

        algorithm_group = Group.objects.get(
            name=settings.ALGORITHMS_CREATORS_GROUP_NAME
        )
        self.users["algorithm"].groups.add(algorithm_group)

        add_product_perm = Permission.objects.get(codename="add_product")
        self.users["air"].user_permissions.add(add_product_perm)

        add_archive_perm = Permission.objects.get(codename="add_archive")
        self.users["archive"].user_permissions.add(add_archive_perm)
        self.users["demo"].user_permissions.add(add_archive_perm)

    def _create_demo_challenge(self):
        demo = Challenge.objects.create(
            short_name="demo",
            description="demo project",
            creator=self.users["demo"],
            use_evaluation=True,
            hidden=False,
            display_forum_link=True,
        )
        demo.add_participant(self.users["demop"])

        Page.objects.create(
            challenge=demo, title="all", permission_level="ALL"
        )
        Page.objects.create(
            challenge=demo, title="reg", permission_level="REG"
        )
        Page.objects.create(
            challenge=demo, title="adm", permission_level="ADM"
        )

        config = WorkspaceTypeConfiguration.objects.create(
            instance_type="ml.t3.medium",
            kind=WorkspaceKindChoices.SAGEMAKER_NOTEBOOK,
        )
        config.enabled_phases.set(demo.phase_set.all())

        Phase.objects.create(challenge=demo, title="Phase 2")

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
            phase.submission_kind = phase.SubmissionKind.ALGORITHM
            phase.evaluation_detail_observable_url = (
                phase.evaluation_comparison_observable_url
            ) = "https://observablehq.com/embed/@grand-challenge/data-fetch-example?cell=*"
            phase.save()

            method = Method(phase=phase, creator=self.users["demo"])
            container = ContentFile(base64.b64decode(b""))
            method.image.save("test.tar", container)
            method.save()

            submission = Submission(phase=phase, creator=self.users["demop"])
            content = ContentFile(base64.b64decode(b""))
            submission.predictions_file.save("test.csv", content)
            submission.save()

            e = Evaluation.objects.create(
                submission=submission,
                method=method,
                status=Evaluation.SUCCESS,
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

    def _create_external_challenge(self):
        ex_challenge = ExternalChallenge.objects.create(
            creator=self.users["demo"],
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

    def _create_io_algorithm(self):
        algorithm = Algorithm.objects.create(
            title="Test Algorithm IO",
            logo=get_temporary_image(),
            use_flexible_inputs=True,
        )
        algorithm.editors_group.user_set.add(
            self.users["algorithm"], self.users["demo"]
        )
        algorithm.users_group.user_set.add(self.users["algorithmuser"])

        algorithm_image = AlgorithmImage(
            creator=self.users["algorithm"], algorithm=algorithm, ready=True
        )
        algorithm_image_path = (
            "tests/resources/gc_demo_algorithm/algorithm_io.tar"
        )
        if os.path.exists(algorithm_image_path):
            with open(
                os.path.join(settings.SITE_ROOT, algorithm_image_path,), "rb",
            ) as f:
                container = File(f)
                algorithm_image.image.save("algorithm_io.tar", container)

        algorithm_image.save()

    def _create_algorithm_demo(self):
        cases_image = grandchallenge.cases.models.Image(
            name="test_image.mha",
            modality=ImagingModality.objects.get(modality="MR"),
            width=128,
            height=128,
            color_space="RGB",
        )
        cases_image.save()

        algorithm = Algorithm.objects.create(
            title="Test Algorithm", logo=get_temporary_image()
        )
        algorithm.editors_group.user_set.add(
            self.users["algorithm"], self.users["demo"]
        )
        algorithm.users_group.user_set.add(self.users["algorithmuser"])
        algorithm.result_template = (
            "{% for key, value in results.metrics.items() -%}"
            "{{ key }}  {{ value }}"
            "{% endfor %}"
        )
        detection_interface = ComponentInterface(
            store_in_database=False,
            relative_path="detection_results.json",
            slug="detection-json-file",
            title="Detection JSON File",
            kind=ComponentInterface.Kind.JSON,
        )
        detection_interface.save()
        algorithm.outputs.add(detection_interface)
        algorithm_image = AlgorithmImage(
            creator=self.users["algorithm"], algorithm=algorithm
        )
        if os.path.isfile(settings.DEMO_ALGORITHM_IMAGE_PATH):
            with open(settings.DEMO_ALGORITHM_IMAGE_PATH, "rb") as f:
                container = File(f)
                algorithm_image.image.save("test_algorithm.tar", container)
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
                    {
                        "type": "Point",
                        "start": [12, 13, 14],
                        "end": [15, 16, 17],
                    }
                ]
            },
        ]
        for res, det in zip(results, detections):
            self.create_job_result(algorithm_image, cases_image, res, det)

    def create_job_result(
        self, algorithm_image, cases_image, result, detection
    ):
        algorithms_job = grandchallenge.algorithms.models.Job(
            creator=self.users["algorithm"],
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
                interface=ComponentInterface.objects.get(
                    slug="results-json-file"
                ),
                value=result,
            )
        )
        civ = ComponentInterfaceValue.objects.create(
            interface=ComponentInterface.objects.get(
                slug="detection-json-file"
            ),
        )
        civ.file.save(
            "detection_results.json",
            ContentFile(
                bytes(
                    json.dumps(detection, ensure_ascii=True, indent=2), "utf-8"
                )
            ),
        )

        algorithms_job.outputs.add(civ)

    def _create_workstation(self):
        w = Workstation.objects.create(
            title=settings.DEFAULT_WORKSTATION_SLUG,
            logo=get_temporary_image(),
            public=True,
        )
        w.add_editor(user=self.users["workstation"])

    def _create_reader_studies(self):
        reader_study = ReaderStudy.objects.create(
            title="Reader Study",
            workstation=Workstation.objects.last(),
            logo=get_temporary_image(),
            description="Test reader study",
        )
        reader_study.editors_group.user_set.add(self.users["readerstudy"])
        reader_study.readers_group.user_set.add(self.users["demo"])

        question = Question.objects.create(
            reader_study=reader_study,
            question_text="foo",
            answer_type=Question.AnswerType.SINGLE_LINE_TEXT,
        )

        answer = Answer.objects.create(
            creator=self.users["readerstudy"], question=question, answer="foo"
        )
        answer.images.add(grandchallenge.cases.models.Image.objects.first())
        answer.save()

    def _create_user_tokens(self):
        # Hard code tokens used in gcapi integration tests
        user_tokens = {
            "admin": "1b9436200001f2eaf57cd77db075cbb60a49a00a",
            "retina": "f1f98a1733c05b12118785ffd995c250fe4d90da",
            "algorithmuser": "dc3526c2008609b429514b6361a33f8516541464",
            "readerstudy": "01614a77b1c0b4ecd402be50a8ff96188d5b011d",
            settings.RETINA_IMPORT_USER_NAME: "e8db90bfbea3c35f40b4537fdca9b3bf1cd78a51",
        }

        out = f"{'*' * 80}\n"
        for user, token in user_tokens.items():
            salt = crypto.create_salt_string()
            digest = crypto.hash_token(token, salt)

            AuthToken(
                token_key=token[: CONSTANTS.TOKEN_KEY_LENGTH],
                digest=digest,
                salt=salt,
                user=self.users[user],
                expiry=None,
            ).save()

            out += f"\t{user} token is: {token}\n"
        out += f"{'*' * 80}\n"
        logger.debug(out)

    @staticmethod
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
