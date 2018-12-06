from grandchallenge.archives.models import Archive
from tests.datastructures_tests.factories import RetinaImageFactory


class ArchiveFactory(factory.DjangoModelFactory):
    class Meta:
        model = Archive

    name = factory.Sequence(lambda n: "Archive {}".format(n))

    @factory.post_generation
    def images(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.images.add(image)
        if create and not extracted:
            self.images.add(RetinaImageFactory())