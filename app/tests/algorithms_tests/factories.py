import factory

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
    Result,
)
from tests.components_tests.factories import ComponentInterfaceValueFactory
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
    creator = factory.SubFactory(UserFactory)

    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            self.inputs.set([*extracted])
        if create and not extracted:
            self.inputs.set(
                [ComponentInterfaceValueFactory(image=ImageFactory())]
            )


class AlgorithmResultFactory(factory.DjangoModelFactory):
    class Meta:
        model = Result

    job = factory.SubFactory(AlgorithmJobFactory)


class AlgorithmPermissionRequestFactory(factory.DjangoModelFactory):
    class Meta:
        model = AlgorithmPermissionRequest

    algorithm = factory.SubFactory(AlgorithmFactory)
    user = factory.SubFactory(UserFactory)
