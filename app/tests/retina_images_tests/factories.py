import random
import factory
from pathlib import Path
from grandchallenge.retina_images.models import RetinaImage
from tests.studies_tests.factories import StudyFactory
from tests.factories import ImageFactory, ImageFileFactory
from tests.cases_tests import RESOURCE_PATH


class ImageFileFactoryWithMHDFile(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image10x10x10.mhd")


class ImageFileFactoryWithRAWFile(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image10x10x10.zraw")


class ImageFactoryWithImageFile(ImageFactory):
    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.files.add(image)
        if create and not extracted:
            self.files.add(ImageFileFactoryWithMHDFile())
            self.files.add(ImageFileFactoryWithRAWFile())


class RetinaImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = RetinaImage

    name = factory.Sequence(lambda n: "RetinaImage {}".format(n))
    image = factory.SubFactory(ImageFactoryWithImageFile)
    study = factory.SubFactory(StudyFactory)
    modality = factory.Iterator([x[0] for x in RetinaImage.MODALITY_CHOICES])
    eye_choice = factory.Iterator(
        [x[0] for x in RetinaImage.EYE_CHOICES]
    )
    voxel_size = [
        random.uniform(0.0, 500.0),
        random.uniform(0.0, 500.0),
        random.uniform(0.0, 500.0),
    ]


