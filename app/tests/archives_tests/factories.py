import factory

from grandchallenge.archives.models import (
    Archive,
    ArchiveItem,
    ArchivePermissionRequest,
)
from tests.factories import UserFactory


class ArchiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Archive

    title = factory.Sequence(lambda n: f"Archive {n}")
    logo = factory.django.ImageField()

    @factory.post_generation
    def algorithms(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if create and extracted:
            self.algorithms.set([*extracted])


class ArchiveItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ArchiveItem

    archive = factory.SubFactory(ArchiveFactory)


class ArchivePermissionRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ArchivePermissionRequest

    archive = factory.SubFactory(ArchiveFactory)
    user = factory.SubFactory(UserFactory)
