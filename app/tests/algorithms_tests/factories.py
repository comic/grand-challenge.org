import factory

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
    Result,
)
from tests.factories import ImageFactory, UserFactory, WorkstationFactory


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


class AlgorithmPermissionRequestFactory(factory.DjangoModelFactory):
    class Meta:
        model = AlgorithmPermissionRequest

    algorithm = factory.SubFactory(AlgorithmFactory)
    user = factory.SubFactory(UserFactory)
