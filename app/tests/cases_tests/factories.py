import datetime

import factory
from factory import fuzzy

from grandchallenge.cases.models import (
    Image,
    ImageFile,
    PostProcessImageTask,
    RawImageUploadSession,
)
from tests.cases_tests import RESOURCE_PATH
from tests.factories import (
    ImageFactory,
    ImageFileFactory,
    ImagingModalityFactory,
)


class ImageFileFactoryWithMHDFile(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image5x6x7.mhd")


class ImageFileFactoryWithRAWFile(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image5x6x7.zraw"
    )


class ImageFileFactoryWithMHDFile2D(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image3x4.mhd")


class ImageFileFactoryWithRAWFile2D(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image3x4.zraw")


class ImageFileFactoryWithMHAFile2DGray16Bit(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "1x2int16.mha")


class ImageFileFactoryWithMHDFile4D(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image10x11x12x13.mhd"
    )


class ImageFileFactoryWithRAWFile4D(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image10x11x12x13.zraw"
    )


class ImageFileFactoryWithMHA16Bit(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "image16bit.mha")


class ImageFileFactoryWithTiff(ImageFileFactory):
    file = factory.django.FileField(from_path=RESOURCE_PATH / "valid_tiff.tif")
    image_type = ImageFile.IMAGE_TYPE_TIFF


class ImageFactoryWithoutImageFile(ImageFactory):
    eye_choice = factory.Iterator([x[0] for x in Image.EYE_CHOICES])
    stereoscopic_choice = factory.Iterator(
        [x[0] for x in Image.STEREOSCOPIC_CHOICES]
    )
    field_of_view = factory.Iterator([x[0] for x in Image.FOV_CHOICES])
    name = factory.Sequence(lambda n: f"Image {n}")
    modality = factory.SubFactory(ImagingModalityFactory, modality="CF")
    color_space = factory.Iterator([x[0] for x in Image.COLOR_SPACES])
    patient_id = factory.Sequence(lambda n: f"Patient {n}")
    patient_name = fuzzy.FuzzyText(prefix="Patient")
    patient_birth_date = fuzzy.FuzzyDate(
        datetime.date(1970, 1, 1), end_date=datetime.date.today()
    )
    patient_age = fuzzy.FuzzyText(length=4)
    patient_sex = factory.Iterator(
        [x[0] for x in Image.PATIENT_SEX_CHOICES] + [""]
    )
    study_date = fuzzy.FuzzyDate(
        datetime.date(1970, 1, 1), end_date=datetime.date.today()
    )
    study_instance_uid = fuzzy.FuzzyText(length=64)
    series_instance_uid = fuzzy.FuzzyText(length=64)
    study_description = factory.Sequence(lambda n: f"Study {n}")
    series_description = factory.Sequence(lambda n: f"Series {n}")


class ImageFactoryWithImageFile(ImageFactoryWithoutImageFile):
    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.files.add(image)
        if create and not extracted:
            ImageFileFactoryWithMHDFile2D(image=self)
            ImageFileFactoryWithRAWFile2D(image=self)

    color_space = Image.COLOR_SPACE_RGB
    width = 3
    height = 4


class ImageFactoryWithImageFile4D(ImageFactoryWithImageFile):
    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.files.add(image)
        if create and not extracted:
            ImageFileFactoryWithMHDFile4D(image=self)
            ImageFileFactoryWithRAWFile4D(image=self)


class ImageFactoryWithImageFileTiff(ImageFactoryWithoutImageFile):
    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.files.add(image)
        if create and not extracted:
            ImageFileFactoryWithTiff(image=self)


class RawImageUploadSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RawImageUploadSession


class PostProcessImageTaskFactory(factory.django.DjangoModelFactory):
    image = factory.SubFactory(ImageFactory)
    status = PostProcessImageTask.PostProcessImageTaskStatusChoices.INITIALIZED

    class Meta:
        model = PostProcessImageTask
