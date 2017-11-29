import factory
from django.contrib.auth.models import User

from comicmodels.models import ComicSite
from evaluation.models import Submission, Job, Method, Result


class ChallengeFactory(factory.DjangoModelFactory):
    class Meta:
        model = ComicSite

    short_name = factory.Sequence(lambda n: f'test_challenge_{n}')


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: 'test_user_%s' % n)
    email = factory.LazyAttribute(lambda u: '%s@test.com' % u.username)
    password = factory.PostGenerationMethodCall('set_password', 'testpasswd')

    is_active = True
    is_staff = False
    is_superuser = False


class SubmissionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Submission

    challenge = factory.SubFactory(ChallengeFactory)
    file = factory.django.FileField()


class JobFactory(factory.DjangoModelFactory):
    class Meta:
        model = Job


class MethodFactory(factory.DjangoModelFactory):
    class Meta:
        model = Method

    challenge = factory.SubFactory(ChallengeFactory)
    image = factory.django.FileField()


class ResultFactory(factory.DjangoModelFactory):
    class Meta:
        model = Result
