import factory
from django.conf import settings

from grandchallenge.cases.models import (
    Image,
    RawImageFile,
    RawImageUploadSession,
)
from tests.cases_tests import RESOURCE_PATH
from tests.factories import (
    ImageFactory,
    ImageFileFactory,
    ImagingModalityFactory,
)
from tests.studies_tests.factories import StudyFactory


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


class ImageFileFactoryWithMHDFile2DLarge(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image128x256RGB.mhd"
    )


class ImageFileFactoryWithRAWFile2DLarge(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image128x256RGB.zraw"
    )


class ImageFileFactoryWithMHDFile3DLarge3Slices(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image128x256x3RGB.mhd"
    )


class ImageFileFactoryWithRAWFile3DLarge3Slices(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image128x256x3RGB.zraw"
    )


class ImageFileFactoryWithMHDFile3DLarge4Slices(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image128x256x4RGB.mhd"
    )


class ImageFileFactoryWithRAWFile3DLarge4Slices(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image128x256x4RGB.zraw"
    )


class ImageFileFactoryWithMHDFile4D(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image10x11x12x13.mhd"
    )


class ImageFileFactoryWithRAWFile4D(ImageFileFactory):
    file = factory.django.FileField(
        from_path=RESOURCE_PATH / "image10x11x12x13.zraw"
    )


class ImageFactoryWithoutImageFile(ImageFactory):
    eye_choice = factory.Iterator([x[0] for x in Image.EYE_CHOICES])
    stereoscopic_choice = factory.Iterator(
        [x[0] for x in Image.STEREOSCOPIC_CHOICES]
    )
    field_of_view = factory.Iterator([x[0] for x in Image.FOV_CHOICES])
    study = factory.SubFactory(StudyFactory)
    name = factory.Sequence(lambda n: f"RetinaImage {n}")
    modality = factory.SubFactory(
        ImagingModalityFactory, modality=settings.MODALITY_CF
    )
    color_space = factory.Iterator([x[0] for x in Image.COLOR_SPACES])


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


class ImageFactoryWithImageFile3D(ImageFactoryWithImageFile):
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

    modality = factory.SubFactory(
        ImagingModalityFactory, modality=settings.MODALITY_OCT
    )


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


class ImageFactoryWithImageFile2DLarge(ImageFactoryWithImageFile):
    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.files.add(image)
        if create and not extracted:
            ImageFileFactoryWithMHDFile2DLarge(image=self)
            ImageFileFactoryWithRAWFile2DLarge(image=self)


class ImageFactoryWithImageFile3DLarge3Slices(ImageFactoryWithImageFile3D):
    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.files.add(image)
        if create and not extracted:
            ImageFileFactoryWithMHDFile3DLarge3Slices(image=self)
            ImageFileFactoryWithRAWFile3DLarge3Slices(image=self)


class ImageFactoryWithImageFile3DLarge4Slices(ImageFactoryWithImageFile3D):
    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            for image in extracted:
                self.files.add(image)
        if create and not extracted:
            ImageFileFactoryWithMHDFile3DLarge4Slices(image=self)
            ImageFileFactoryWithRAWFile3DLarge4Slices(image=self)


class RawImageUploadSessionFactory(factory.DjangoModelFactory):
    class Meta:
        model = RawImageUploadSession


class RawImageFileFactory(factory.DjangoModelFactory):
    class Meta:
        model = RawImageFile

    upload_session = factory.SubFactory(RawImageUploadSessionFactory)
