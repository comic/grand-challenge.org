import factory
from django.conf import settings

from comic.eyra_algorithms.models import Algorithm, Interface, Input, Implementation
from comic.eyra_benchmarks.models import Benchmark
from comic.eyra_data.models import DataType

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


class DataTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = DataType
    name = factory.Sequence(lambda n: "Test data type %03d" % n)
    description = "Test datatype"


class InputFactory(factory.DjangoModelFactory):
    class Meta:
        model = Input
    name = factory.Sequence(lambda n: "Test input %03d" % n)
    # interface = factory.SubFactory(InterfaceFactory)
    type = factory.SubFactory(DataTypeFactory)


class InterfaceFactory(factory.DjangoModelFactory):
    class Meta:
        model = Interface
    name = factory.Sequence(lambda n: "Test interface %03d" % n)
    output_type = factory.SubFactory(DataTypeFactory)
    input1 = factory.RelatedFactory(InputFactory, 'interface')


class EvaluationInterfaceFactory(factory.DjangoModelFactory):
    class Meta:
        model = Interface
    name = factory.Sequence(lambda n: "Test interface %03d" % n)
    output_type = factory.SubFactory(DataTypeFactory, name='OutputMetrics')
    input1 = factory.RelatedFactory(InputFactory, 'interface', name="ground_truth")
    input2 = factory.RelatedFactory(InputFactory, 'interface', name="implementation_output")


class AlgorithmFactory(factory.DjangoModelFactory):
    class Meta:
        model = Algorithm

    creator = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: "Test algorithm %03d" % n)
    description = 'Test benchmark description'
    interface = factory.SubFactory(InterfaceFactory)


class ImplementationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Implementation

    creator = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: "Test implementation %03d" % n)
    description = 'Test benchmark description'
    image = 'eyra/test:latest'
    version = '1'
    algorithm = factory.SubFactory(AlgorithmFactory)