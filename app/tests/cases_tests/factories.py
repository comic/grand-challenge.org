import factory
from django.conf import settings
from grandchallenge.cases.models import Image
from tests.studies_tests.factories import StudyFactory
from tests.factories import (
    ImageFactory,
    ImageFileFactory,
    ImagingModalityFactory,
)
from tests.cases_tests import RESOURCE_PATH


class ImageFileFactoryWithMHDFile(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image5x6x7.mhd")


class ImageFileFactoryWithRAWFile(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image5x6x7.zraw"
    )


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

    eye_choice = factory.Iterator([x[0] for x in Image.EYE_CHOICES])
    stereoscopic_choice = factory.Iterator(
        [x[0] for x in Image.STEREOSCOPIC_CHOICES]
    )
    field_of_view = factory.Iterator([x[0] for x in Image.FOV_CHOICES])
    study = factory.SubFactory(StudyFactory)
    name = factory.Sequence(lambda n: "RetinaImage {}".format(n))
    modality = factory.SubFactory(
        ImagingModalityFactory, modality=settings.MODALITY_CF
    )
    color_space = Image.COLOR_SPACE_RGB
