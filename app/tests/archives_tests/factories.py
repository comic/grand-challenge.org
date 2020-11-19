import factory

from grandchallenge.archives.models import Archive, ArchivePermissionRequest
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import ImageFactory, UserFactory


class ArchiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Archive

    title = factory.Sequence(lambda n: f"Archive {n}")

    @factory.post_generation
    def images(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            self.images.set([*extracted])
        if create and not extracted:
            self.images.add(ImageFactory())

    @factory.post_generation
    def algorithms(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            self.algorithms.set([*extracted])
        if create and not extracted:
            self.algorithms.add(AlgorithmFactory())


class ArchivePermissionRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ArchivePermissionRequest

    archive = factory.SubFactory(ArchiveFactory)
    user = factory.SubFactory(UserFactory)
