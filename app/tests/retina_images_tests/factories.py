import random
import factory
from pathlib import Path
# from grandchallenge.retina_images.models import RetinaImage
from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import ImagingModality
from tests.studies_tests.factories import StudyFactory
from tests.factories import ImageFactory, ImageFileFactory, ImagingModalityFactory
from tests.cases_tests import RESOURCE_PATH


class ImageFileFactoryWithMHDFile(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image5x6x7.mhd")


class ImageFileFactoryWithRAWFile(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image5x6x7.zraw")


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
            ImageFileFactoryWithMHDFile(image=self)
            ImageFileFactoryWithRAWFile(image=self)
    eye_choice = factory.Iterator(
        [x[0] for x in Image.EYE_CHOICES]
    )
    study = factory.SubFactory(StudyFactory)
    name = factory.Sequence(lambda n: "RetinaImage {}".format(n))
    modality = factory.SubFactory(ImagingModalityFactory, modality=ImagingModality.MODALITY_CF)
