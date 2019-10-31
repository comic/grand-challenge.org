import factory

from grandchallenge.archives.models import Archive
from tests.cases_tests.factories import ImageFactory


class ArchiveFactory(factory.DjangoModelFactory):
    class Meta:
        model = Archive

    name = factory.Sequence(lambda n: f"Archive {n}")

    @factory.post_generation
    def images(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.images.add(image)
        if create and not extracted:
            self.images.add(ImageFactory())
