import base64

from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.management import BaseCommand
from userena.models import UserenaSignup
from django.contrib.auth.models import Group

from grandchallenge.challenges.models import (
    Challenge,
    ExternalChallenge,
    TaskType,
    BodyRegion,
    BodyStructure,
    ImagingModality,
)
from grandchallenge.evaluation.models import Result, Submission, Job, Method
from grandchallenge.pages.models import Page


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Creates the main project, demo user and demo challenge
        """
        # Set the default domain that is used in RequestFactory
        site = Site.objects.get(pk=settings.SITE_ID)

        if site.domain == "gc.localhost":
            # Already initialised
            return

        site.domain = "gc.localhost"
        site.name = "Grand Challenge"
        site.save()

        page = FlatPage.objects.create(
            url="/about/",
            title="About",
            content="<p>You can add flatpages via django admin</p>",
        )
        page.sites.add(site)

        demoadmin = UserenaSignup.objects.create_user(
            username="demo",
            email="demo@example.com",
            password="demo",
            active=True,
        )
        demoparticipant = UserenaSignup.objects.create_user(
            username="demop",
            email="demop@example.com",
            password="demop",
            active=True,
        )
        UserenaSignup.objects.create_user(
            username="user",
            email="user@example.com",
            password="user",
            active=True,
        )
        adminuser = UserenaSignup.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin",
            active=True,
        )
        adminuser.is_staff = True
        adminuser.save()
        demo = Challenge.objects.create(
            short_name="demo",
            description="demo project",
            creator=demoadmin,
            use_evaluation=True,
            hidden=False,
        )
        demo.add_participant(demoparticipant)
        Page.objects.create(challenge=demo, title="all", permission_lvl="ALL")
        Page.objects.create(challenge=demo, title="reg", permission_lvl="REG")
        Page.objects.create(challenge=demo, title="adm", permission_lvl="ADM")

        method = Method(challenge=demo, creator=demoadmin)
        container = ContentFile(base64.b64decode(b""))
        method.image.save("test.tar", container)
        method.save()

        submission = Submission(challenge=demo, creator=demoparticipant)
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

        ex_challenge = ExternalChallenge.objects.create(
            creator=demoadmin,
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

        retina_demo = UserenaSignup.objects.create_user(
            username="retina_demo",
            email="retina@example.com",
            password="retina",
            active=True,
        )
        retina_group = Group.objects.get(
            name=settings.RETINA_GRADERS_GROUP_NAME
        )
        retina_demo.groups.add(retina_group)
