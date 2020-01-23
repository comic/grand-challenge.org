import hashlib
from datetime import timedelta
from uuid import uuid4

import factory
import factory.fuzzy
from django.conf import settings
from django.utils import timezone

from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.challenges.models import (
    Challenge,
    ExternalChallenge,
    ImagingModality,
)
from grandchallenge.datasets.models import AnnotationSet, ImageSet
from grandchallenge.evaluation.models import Job, Method, Result, Submission
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.pages.models import Page
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.policies.models import Policy
from grandchallenge.teams.models import Team, TeamMember
from grandchallenge.workstation_configs.models import WorkstationConfig
from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)

SUPER_SECURE_TEST_PASSWORD = "testpasswd"


def hash_sha256(s):
    m = hashlib.sha256()
    m.update(s.encode())
    return f"sha256:{m.hexdigest()}"


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: f"test_user_{n:04}")
    email = factory.LazyAttribute(lambda u: "%s@test.com" % u.username)
    password = factory.PostGenerationMethodCall(
        "set_password", SUPER_SECURE_TEST_PASSWORD
    )
    is_active = True
    is_staff = False
    is_superuser = False


class ChallengeFactory(factory.DjangoModelFactory):
    class Meta:
        model = Challenge

    short_name = factory.Sequence(lambda n: f"test-challenge-{n}")
    creator = factory.SubFactory(UserFactory)


class ExternalChallengeFactory(factory.DjangoModelFactory):
    class Meta:
        model = ExternalChallenge

    short_name = factory.Sequence(lambda n: f"test_external_challenge{n}")
    homepage = factory.Faker("url")


class PageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Page

    challenge = factory.SubFactory(ChallengeFactory)
    title = factory.Sequence(lambda n: f"page_{n}")
    html = factory.LazyAttribute(lambda t: f"<h2>{t.title}</h2>")


class RegistrationRequestFactory(factory.DjangoModelFactory):
    class Meta:
        model = RegistrationRequest

    user = factory.SubFactory(UserFactory)
    challenge = factory.SubFactory(ChallengeFactory)


class MethodFactory(factory.DjangoModelFactory):
    class Meta:
        model = Method

    challenge = factory.SubFactory(ChallengeFactory)
    image = factory.django.FileField()
    image_sha256 = factory.sequence(lambda n: hash_sha256(f"image{n}"))


class SubmissionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Submission

    challenge = factory.SubFactory(ChallengeFactory)
    file = factory.django.FileField()
    creator = factory.SubFactory(UserFactory)


class JobFactory(factory.DjangoModelFactory):
    class Meta:
        model = Job

    method = factory.SubFactory(MethodFactory)
    submission = factory.SubFactory(SubmissionFactory)


class ResultFactory(factory.DjangoModelFactory):
    class Meta:
        model = Result

    job = factory.SubFactory(JobFactory)


class TeamFactory(factory.DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: "test_team_%s" % n)
    challenge = factory.SubFactory(ChallengeFactory)


class TeamMemberFactory(factory.DjangoModelFactory):
    class Meta:
        model = TeamMember

    team = factory.SubFactory(TeamFactory)


class UploadSessionFactory(factory.DjangoModelFactory):
    class Meta:
        model = RawImageUploadSession


class ImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Image

    origin = factory.SubFactory(UploadSessionFactory)
    width = 128
    height = 128


class ImageFileFactory(factory.DjangoModelFactory):
    class Meta:
        model = ImageFile

    image = factory.SubFactory(ImageFactory)
    image_type = ImageFile.IMAGE_TYPE_MHD
    file = factory.django.FileField()


class ImageSetFactory(factory.DjangoModelFactory):
    class Meta:
        model = ImageSet


class AnnotationSetFactory(factory.DjangoModelFactory):
    class Meta:
        model = AnnotationSet

    creator = factory.SubFactory(UserFactory)
    base = factory.SubFactory(ImageSetFactory)


class ImagingModalityFactory(factory.DjangoModelFactory):
    class Meta:
        model = ImagingModality
        django_get_or_create = ("modality",)

    modality = factory.sequence(lambda n: f"Modality {n}")


class StagedFileFactory(factory.DjangoModelFactory):
    class Meta:
        model = StagedFile

    file_id = factory.LazyFunction(uuid4)
    file = factory.django.FileField()
    timeout = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    start_byte = 0
    end_byte = factory.LazyAttribute(lambda s: s.file.size)
    client_filename = factory.LazyAttribute(lambda s: s.file.name)


class WorkstationConfigFactory(factory.DjangoModelFactory):
    class Meta:
        model = WorkstationConfig


class WorkstationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Workstation

    title = factory.sequence(lambda n: f"Workstation {n}")
    logo = factory.django.ImageField()


class WorkstationImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = WorkstationImage

    workstation = factory.SubFactory(WorkstationFactory)
    creator = factory.SubFactory(UserFactory)
    image = factory.django.FileField()
    image_sha256 = factory.sequence(lambda n: hash_sha256(f"image{n}"))


class SessionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Session

    creator = factory.SubFactory(UserFactory)
    workstation_image = factory.SubFactory(WorkstationImageFactory)


class FuzzyFloatCoordinatesList(factory.fuzzy.BaseFuzzyAttribute):
    def __init__(self, size=None):
        self.size = size

    def fuzz(self):
        if self.size is None:
            size = factory.fuzzy.random.randgen.randint(2, 30)
        else:
            size = self.size

        fuzzy_list = []
        for _ in range(size):
            fuzzy_list.append(
                [
                    round(
                        factory.fuzzy.random.randgen.uniform(0.0, 1000.0), 12
                    ),
                    round(
                        factory.fuzzy.random.randgen.uniform(0.0, 1000.0), 12
                    ),
                ]
            )

        if size == 1:
            return fuzzy_list[0]

        return fuzzy_list


class PolicyFactory(factory.DjangoModelFactory):
    class Meta:
        model = Policy
