import base64
import logging
from io import BytesIO

from PIL import Image
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management import BaseCommand
from rest_framework.authtoken.models import Token
from userena.models import UserenaSignup

import grandchallenge.cases.models
from grandchallenge.algorithms.models import Algorithm, AlgorithmImage
from grandchallenge.challenges.models import (
    BodyRegion,
    BodyStructure,
    Challenge,
    ExternalChallenge,
    ImagingModality,
    TaskType,
)
from grandchallenge.evaluation.models import Job, Method, Result, Submission
from grandchallenge.pages.models import Page
from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
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
        ]
        self.users = self._create_users(usernames=default_users)

        self._set_user_permissions()
        self._create_user_tokens()
        self._create_demo_challenge()
        self._create_external_challenge()
        self._create_workstation()
        self._create_algorithm_demo()
        self._create_reader_studies()
        self._log_tokens()

    def _create_flatpages(self, site):
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
            users[username] = UserenaSignup.objects.create_user(
                username=username,
                email=f"{username}@example.com",
                password=username,
                active=True,
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

        algorithm_group = Group.objects.get(
            name=settings.ALGORITHMS_CREATORS_GROUP_NAME
        )
        self.users["algorithm"].groups.add(algorithm_group)

    def _create_user_tokens(self):
        Token.objects.get_or_create(
            user=self.users["admin"],
            key="1b9436200001f2eaf57cd77db075cbb60a49a00a",
        )
        Token.objects.get_or_create(
            user=self.users["retina"],
            key="f1f98a1733c05b12118785ffd995c250fe4d90da",
        )

    def _create_demo_challenge(self):
        demo = Challenge.objects.create(
            short_name="demo",
            description="demo project",
            creator=self.users["demo"],
            use_evaluation=True,
            hidden=False,
        )
        demo.add_participant(self.users["demop"])

        Page.objects.create(challenge=demo, title="all", permission_lvl="ALL")
        Page.objects.create(challenge=demo, title="reg", permission_lvl="REG")
        Page.objects.create(challenge=demo, title="adm", permission_lvl="ADM")

        method = Method(challenge=demo, creator=self.users["demo"])
        container = ContentFile(base64.b64decode(b""))
        method.image.save("test.tar", container)
        method.save()

        submission = Submission(challenge=demo, creator=self.users["demop"])
        content = ContentFile(base64.b64decode(b""))
        submission.file.save("test.csv", content)
        submission.save()

        job = Job.objects.create(submission=submission, method=method)

        Result.objects.create(
            metrics={
                "acc": {"mean": 0.5, "std": 0.1},
                "dice": {"mean": 0.71, "std": 0.05},
            },
            job=job,
        )

        demo.evaluation_config.score_title = "Accuracy ± std"
        demo.evaluation_config.score_jsonpath = "acc.mean"
        demo.evaluation_config.score_error_jsonpath = "acc.std"
        demo.evaluation_config.extra_results_columns = [
            {
                "title": "Dice ± std",
                "path": "dice.mean",
                "error_path": "dice.std",
                "order": "desc",
            }
        ]
        demo.evaluation_config.save()

    def _create_external_challenge(self):
        ex_challenge = ExternalChallenge.objects.create(
            creator=self.users["demo"],
            homepage="https://www.example.com",
            short_name="EXAMPLE2018",
            title="Example External Challenge 2018",
            description="An example of an external challenge",
            event_name="Example Event",
            event_url="https://www.example.com/2018",
            publication_journal_name="Nature",
            publication_url="https://doi.org/10.1038/s41586-018-0367-9",
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

        mr_modality = ImagingModality.objects.get(modality="MR")
        ex_challenge.modalities.add(mr_modality)
        ex_challenge.save()

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
        algorithm.editors_group.user_set.add(self.users["algorithm"])

        algorithm_image = AlgorithmImage(
            creator=self.users["algorithm"], algorithm=algorithm
        )
        container = ContentFile(base64.b64decode(b""))
        algorithm_image.image.save("test_algorithm.tar", container)
        algorithm_image.save()

        algorithms_job = grandchallenge.algorithms.models.Job(
            creator=self.users["algorithm"],
            algorithm_image=algorithm_image,
            image=cases_image,
        )
        algorithms_job.save()

        algorithms_result = grandchallenge.algorithms.models.Result(
            output={"cancer_score": 0.5}, job=algorithms_job
        )
        algorithms_result.save()
        algorithms_result.images.add(cases_image)

    def _create_workstation(self):
        w = Workstation.objects.create(
            title=settings.DEFAULT_WORKSTATION_SLUG, logo=get_temporary_image()
        )
        w.add_user(user=self.users["readerstudy"])
        w.add_editor(user=self.users["workstation"])
        w.add_user(user=self.users["algorithm"])

    def _create_reader_studies(self):
        reader_study = ReaderStudy.objects.create(
            title="Reader Study",
            workstation=Workstation.objects.first(),
            logo=get_temporary_image(),
        )
        reader_study.editors_group.user_set.add(self.users["readerstudy"])
        reader_study.readers_group.user_set.add(self.users["demo"])

        question = Question.objects.create(
            reader_study=reader_study,
            question_text="foo",
            answer_type=Question.ANSWER_TYPE_SINGLE_LINE_TEXT,
        )

        answer = Answer.objects.create(
            creator=self.users["readerstudy"], question=question, answer="foo"
        )
        answer.images.add(grandchallenge.cases.models.Image.objects.first())
        answer.save()

    @staticmethod
    def _log_tokens():
        out = [f"\t{t.user} token is: {t}\n" for t in Token.objects.all()]
        logger.debug(f"{'*' * 80}\n{''.join(out)}{'*' * 80}")
