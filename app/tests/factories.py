import hashlib

import factory
from django.conf import settings

from challenges.models import Challenge
from evaluation.models import Submission, Job, Method, Result
from pages.models import Page
from participants.models import RegistrationRequest
from teams.models import Team, TeamMember
from uploads.models import UploadModel

SUPER_SECURE_TEST_PASSWORD = 'testpasswd'


class ChallengeFactory(factory.DjangoModelFactory):

    class Meta:
        model = Challenge

    short_name = factory.Sequence(lambda n: f'test_challenge_{n}')


class PageFactory(factory.DjangoModelFactory):

    class Meta:
        model = Page

    challenge = factory.SubFactory(ChallengeFactory)
    title = factory.Sequence(lambda n: f'page_{n}')
    html = factory.LazyAttribute(lambda t: f'<h2>{t.title}</h2>')


class UserFactory(factory.DjangoModelFactory):

    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: f'test_user_{n:04}')
    email = factory.LazyAttribute(lambda u: '%s@test.com' % u.username)
    password = factory.PostGenerationMethodCall(
        'set_password', SUPER_SECURE_TEST_PASSWORD
    )
    is_active = True
    is_staff = False
    is_superuser = False


class UploadFactory(factory.DjangoModelFactory):

    class Meta:
        model = UploadModel

    challenge = factory.SubFactory(ChallengeFactory)
    file = factory.django.FileField()
    user = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f'file_{n}')


class RegistrationRequestFactory(factory.DjangoModelFactory):

    class Meta:
        model = RegistrationRequest

    user = factory.SubFactory(UserFactory)
    challenge = factory.SubFactory(ChallengeFactory)


def hash_sha256(s):
    m = hashlib.sha256()
    m.update(s.encode())
    return f'sha256:{m.hexdigest()}'


class MethodFactory(factory.DjangoModelFactory):

    class Meta:
        model = Method

    challenge = factory.SubFactory(ChallengeFactory)
    image = factory.django.FileField()
    image_sha256 = factory.sequence(lambda n: hash_sha256(f'image{n}'))


class SubmissionFactory(factory.DjangoModelFactory):

    class Meta:
        model = Submission

    challenge = factory.SubFactory(ChallengeFactory)
    file = factory.django.FileField()


class JobFactory(factory.DjangoModelFactory):

    class Meta:
        model = Job

    challenge = factory.SubFactory(ChallengeFactory)
    method = factory.SubFactory(MethodFactory)
    submission = factory.SubFactory(SubmissionFactory)


class ResultFactory(factory.DjangoModelFactory):

    class Meta:
        model = Result

    challenge = factory.SubFactory(ChallengeFactory)


class TeamFactory(factory.DjangoModelFactory):

    class Meta:
        model = Team

    name = factory.Sequence(lambda n: 'test_team_%s' % n)
    challenge = factory.SubFactory(ChallengeFactory)


class TeamMemberFactory(factory.DjangoModelFactory):

    class Meta:
        model = TeamMember

    team = factory.SubFactory(TeamFactory)
