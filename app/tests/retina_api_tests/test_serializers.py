import random

import pytest
from PIL import Image as PILImage
from django.conf import settings
from django.http import Http404

from grandchallenge.retina_api.serializers import (
    BytesImageSerializer,
    PILImageSerializer,
    TreeArchiveSerializer,
    TreeImageSerializer,
    TreeObjectSerializer,
    TreeStudySerializer,
)
from tests.archives_tests.factories import ArchiveFactory
from tests.cases_tests.factories import (
    ImageFactoryWithImageFile,
    ImageFactoryWithImageFile2DLarge,
    ImageFactoryWithImageFile3D,
    ImageFactoryWithImageFile3DLarge3Slices,
    ImageFactoryWithImageFile3DLarge4Slices,
    ImageFactoryWithoutImageFile,
)
from tests.serializer_helpers import do_test_serializer_fields
from tests.studies_tests.factories import StudyFactory


@pytest.mark.django_db
class TestPILImageSerializer:
    def test_non_existant_image_files(self):
        image = ImageFactoryWithoutImageFile()
        serializer = PILImageSerializer(image)
        with pytest.raises(Http404):
            assert serializer.data

    @pytest.mark.parametrize(
        "factory", [ImageFactoryWithImageFile, ImageFactoryWithImageFile3D]
    )
    def test_image_no_parameters(self, factory):
        image = factory()
        serializer = PILImageSerializer(image)
        image_itk = image.get_sitk_image()
        image_pil = PILImageSerializer.convert_itk_to_pil(image_itk)
        assert serializer.data == image_pil

    @pytest.mark.parametrize(
        "factory",
        [
            ImageFactoryWithImageFile2DLarge,
            ImageFactoryWithImageFile3DLarge3Slices,
            ImageFactoryWithImageFile3DLarge4Slices,
        ],
    )
    @pytest.mark.parametrize("max_dimension", ["default", "random"])
    def test_image_resizes(self, factory, max_dimension):
        if max_dimension == "random":
            max_dimension = random.randint(1, 255)
        else:
            max_dimension = settings.RETINA_DEFAULT_THUMBNAIL_SIZE
        image = factory()
        serializer_context = {"width": max_dimension, "height": max_dimension}
        serializer = PILImageSerializer(image, context=serializer_context)
        image_itk = image.get_sitk_image()
        image_pil = PILImageSerializer.convert_itk_to_pil(image_itk)
        image_pil.thumbnail((max_dimension, max_dimension), PILImage.ANTIALIAS)
        assert serializer.data == image_pil
        assert serializer.data.size == image_pil.size
        assert max(serializer.data.size) == max_dimension


@pytest.mark.django_db
class TestBytesImageSerializer:
    def test_non_existant_image_files(self):
        image = ImageFactoryWithoutImageFile()
        serializer = BytesImageSerializer(image)
        with pytest.raises(Http404):
            assert serializer.data

    @pytest.mark.parametrize(
        "factory", [ImageFactoryWithImageFile, ImageFactoryWithImageFile3D]
    )
    def test_image_no_parameters(self, factory):
        image = factory()
        serializer = BytesImageSerializer(image)
        image_itk = image.get_sitk_image()
        image_pil = PILImageSerializer.convert_itk_to_pil(image_itk)
        image_bytes = BytesImageSerializer.create_thumbnail_as_bytes_io(
            image_pil
        )
        assert serializer.data == image_bytes


@pytest.mark.django_db
@pytest.mark.parametrize(
    "serializer_data",
    (
        (
            {
                "unique": False,
                "factory": ArchiveFactory,
                "serializer": TreeObjectSerializer,
                "fields": ("id", "name"),
            },
            {
                "unique": False,
                "factory": StudyFactory,
                "serializer": TreeStudySerializer,
                "fields": ("name", "patient"),
            },
            {
                "unique": False,
                "factory": ArchiveFactory,
                "serializer": TreeArchiveSerializer,
                "fields": ("name",),
            },
            {
                "unique": False,
                "factory": ImageFactoryWithoutImageFile,
                "serializer": TreeImageSerializer,
                "fields": (
                    "id",
                    "name",
                    "eye_choice",
                    "modality",
                    "study",
                    "archive_set",
                ),
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)
