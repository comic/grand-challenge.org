import datetime
import hashlib

import factory
import factory.fuzzy
from django.conf import settings
from django.contrib.auth.models import Group
from factory import fuzzy

from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.challenges.models import Challenge, ChallengeRequest
from grandchallenge.modalities.models import ImagingModality
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


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"test_user_{n:04}")
    email = factory.LazyAttribute(lambda u: "%s@example.com" % u.username)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted or SUPER_SECURE_TEST_PASSWORD)
        self.save()


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = factory.Sequence(lambda n: f"Group {n}")


class ChallengeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Challenge

    short_name = factory.Sequence(lambda n: f"test-challenge-{n}")
    creator = factory.SubFactory(UserFactory)


class ChallengeRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChallengeRequest

    creator = factory.SubFactory(UserFactory)
    short_name = factory.Sequence(lambda n: f"test-challenge-{n}")
    title = factory.fuzzy.FuzzyText()
    start_date = fuzzy.FuzzyDate(datetime.date(1970, 1, 1))
    end_date = fuzzy.FuzzyDate(datetime.date(1971, 1, 1))
    expected_number_of_teams = 10
    inference_time_limit_in_minutes = 10
    average_size_of_test_image_in_mb = 10
    phase_1_number_of_submissions_per_team = 10
    phase_2_number_of_submissions_per_team = 0
    phase_1_number_of_test_images = 100
    phase_2_number_of_test_images = 0
    number_of_tasks = 1
    structured_challenge_submission_doi = "10.5281/zenodo.6362337"


class PageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Page

    challenge = factory.SubFactory(ChallengeFactory)
    display_title = factory.Sequence(lambda n: f"page_{n}")
    html = factory.LazyAttribute(lambda t: f"<h2>{t.display_title}</h2>")


class RegistrationRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegistrationRequest

    user = factory.SubFactory(UserFactory)
    challenge = factory.SubFactory(ChallengeFactory)


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: "test_team_%s" % n)
    challenge = factory.SubFactory(ChallengeFactory)


class TeamMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeamMember

    team = factory.SubFactory(TeamFactory)


class UploadSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RawImageUploadSession


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image
        skip_postgeneration_save = True

    origin = factory.SubFactory(UploadSessionFactory)
    width = 128
    height = 128
    name = factory.Sequence(lambda n: f"image_{n}")


class ImageFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ImageFile

    image = factory.SubFactory(ImageFactory)
    image_type = ImageFile.IMAGE_TYPE_MHD
    file = factory.django.FileField()


class ImagingModalityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ImagingModality
        django_get_or_create = ("modality",)

    modality = factory.sequence(lambda n: f"Modality {n}")


class WorkstationConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkstationConfig


class WorkstationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workstation

    title = factory.sequence(lambda n: f"Workstation {n}")
    logo = factory.django.ImageField()


class WorkstationImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkstationImage

    workstation = factory.SubFactory(WorkstationFactory)
    creator = factory.SubFactory(UserFactory)
    image = factory.django.FileField()
    image_sha256 = factory.sequence(lambda n: hash_sha256(f"image{n}"))


class SessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Session

    creator = factory.SubFactory(UserFactory)
    workstation_image = factory.SubFactory(WorkstationImageFactory)


class PolicyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Policy
