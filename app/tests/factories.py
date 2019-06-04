import factory
from django.conf import settings

from grandchallenge.eyra_benchmarks.models import Benchmark

SUPER_SECURE_TEST_PASSWORD = "testpasswd"


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


class BenchmarkFactory(factory.DjangoModelFactory):
    class Meta:
        model = Benchmark

    creator = factory.SubFactory(UserFactory)
    name = 'Test-benchmark'
    short_description = 'Test benchmark short description'
    description = 'Test benchmark description'
    data_description = 'Test bm data description'
    truth_description = 'Test bm truth description'
    metrics_description = 'Test bm metrics description'
