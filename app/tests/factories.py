import datetime
import hashlib

import factory
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.timezone import now
from factory import fuzzy

from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    OnboardingTask,
)
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.pages.models import Page
from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationRequest,
)
from grandchallenge.policies.models import Policy
from grandchallenge.teams.models import Team, TeamMember
from grandchallenge.workstation_configs.models import WorkstationConfig
from grandchallenge.workstations.models import (
    Session,
    Workstation,
    WorkstationImage,
)


def activate_2fa(*, user):
    """Activate 2FA for a user including recovery codes."""
    totp_authenticator = Authenticator(type=Authenticator.Type.TOTP)
    totp_authenticator.wrap().activate(
        user=user,
        # Setting a blank secret here, but this is only for use in tests
        secret="",
    )

    recovery_codes_authenticator = Authenticator(
        type=Authenticator.Type.RECOVERY_CODES
    )
    recovery_codes_authenticator.wrap().activate(user=user)


def get_unused_recovery_codes(*, user):
    device = Authenticator.objects.get(
        user=user, type=Authenticator.Type.RECOVERY_CODES
    )
    return device.wrap().get_unused_codes()


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
        if create and extracted:
            self.set_password(extracted)
            self.save()

    @factory.post_generation
    def _generate_staff_totp(self, create, extracted, **kwargs):
        if create and self.is_staff:
            # 2FA is required for staff users
            activate_2fa(user=self)


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = factory.Sequence(lambda n: f"Group {n}")


class ChallengeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Challenge

    short_name = factory.Sequence(lambda n: f"test-challenge-{n}")
    creator = factory.SubFactory(UserFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = super()._create(model_class, *args, **kwargs)
        # Get a fresh copy with annotations
        return Challenge.objects.with_available_compute().get(pk=obj.pk)


class ChallengeRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChallengeRequest

    creator = factory.SubFactory(UserFactory)
    short_name = factory.Sequence(lambda n: f"test-challenge-{n}")
    title = factory.fuzzy.FuzzyText()
    start_date = fuzzy.FuzzyDate(
        datetime.date(1970, 1, 1), end_date=datetime.date.today()
    )
    end_date = fuzzy.FuzzyDate(
        datetime.date(1971, 1, 1), end_date=datetime.date.today()
    )
    task_ids = [1, 2]
    algorithm_maximum_settable_memory_gb_for_tasks = [32, 32]
    algorithm_selectable_gpu_type_choices_for_tasks = [
        ["", "T4"],
        ["", "A10G", "T4"],
    ]
    average_size_test_image_mb_for_tasks = [10, 100]
    inference_time_average_minutes_for_tasks = [5, 10]
    task_id_for_phases = [1, 1, 2, 2]
    number_of_submissions_per_team_for_phases = [10, 1, 10, 1]
    number_of_teams_for_phases = [10, 10, 10, 10]
    number_of_test_images_for_phases = [3, 100, 3, 100]
    structured_challenge_submission_doi = "10.5281/zenodo.6362337"


class PageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Page

    challenge = factory.SubFactory(ChallengeFactory)
    display_title = factory.Sequence(lambda n: f"page_{n}")
    content_markdown = factory.LazyAttribute(lambda t: f"## {t.display_title}")


class RegistrationRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegistrationRequest

    user = factory.SubFactory(UserFactory)
    challenge = factory.SubFactory(ChallengeFactory)


class RegistrationQuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegistrationQuestion

    question_text = factory.Sequence(lambda n: f"Text {n}")
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


class OnboardingTaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OnboardingTask

    challenge = factory.SubFactory(ChallengeFactory)
    title = factory.sequence(lambda n: f"Task {n}")
    deadline = factory.LazyFunction(now)
