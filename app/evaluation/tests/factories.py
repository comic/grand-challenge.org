import factory
from django.contrib.auth.models import User

from comicmodels.models import ComicSite
from evaluation.models import Submission, Job, Method, Result


class ComicSiteFactory(factory.Factory):
    class Meta:
        model = ComicSite

    short_name = 'test_challenge'


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: 'test_user_%s' % n)
    email = factory.LazyAttribute(lambda u: '%s@test.com' % u.username)
    password = factory.PostGenerationMethodCall('set_password', 'testpasswd')

    is_active = True
    is_staff = False
    is_superuser = False


class SubmissionFactory(factory.Factory):
    class Meta:
        model = Submission

    challenge = factory.SubFactory(ComicSiteFactory)


class JobFactory(factory.Factory):
    class Meta:
        model = Job


class MethodFactory(factory.Factory):
    class Meta:
        model = Method


class ResultFactory(factory.Factory):
    class Meta:
        model = Result
