import factory
from grandchallenge.algorithms.models import (
    AlgorithmImage,
    Job,
    Result,
    Algorithm,
)
from tests.factories import ImageFactory, WorkstationFactory, UserFactory


class AlgorithmFactory(factory.DjangoModelFactory):
    class Meta:
        model = Algorithm

    title = factory.sequence(lambda n: f"Algorithm {n}")
    logo = factory.django.ImageField()
    workstation = factory.SubFactory(WorkstationFactory)


class AlgorithmImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = AlgorithmImage

    algorithm = factory.SubFactory(AlgorithmFactory)
    creator = factory.SubFactory(UserFactory)


class AlgorithmJobFactory(factory.DjangoModelFactory):
    class Meta:
        model = Job

    algorithm_image = factory.SubFactory(AlgorithmImageFactory)
    image = factory.SubFactory(ImageFactory)
    creator = factory.SubFactory(UserFactory)


class AlgorithmResultFactory(factory.DjangoModelFactory):
    class Meta:
        model = Result

    job = factory.SubFactory(AlgorithmJobFactory)
