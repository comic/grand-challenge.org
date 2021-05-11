import random
from base64 import b64decode
from io import BytesIO

import pytest
from PIL import Image as PILImage
from django.conf import settings
from django.http import Http404

from grandchallenge.retina_api.serializers import (
    B64ImageSerializer,
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
class TestB64ImageSerializer:
    def test_non_existant_image_files(self):
        image = ImageFactoryWithoutImageFile()
        serializer = B64ImageSerializer(image)
        with pytest.raises(Http404):
            assert serializer.data

    @pytest.mark.parametrize(
        "factory", [ImageFactoryWithImageFile, ImageFactoryWithImageFile3D]
    )
    def test_image_no_parameters(self, factory):
        image = factory()
        serializer = B64ImageSerializer(image)
        image_itk = image.get_sitk_image()
        image_pil = B64ImageSerializer.convert_itk_to_pil(image_itk)
        image_bytes = B64ImageSerializer.create_thumbnail_as_b64(image_pil)
        assert serializer.data["content"] == image_bytes

        decoded_image_pil = PILImage.open(
            BytesIO(b64decode(serializer.data["content"]))
        )
        assert decoded_image_pil.size == image_pil.size

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
        serializer = B64ImageSerializer(image, context=serializer_context)
        image_itk = image.get_sitk_image()
        image_pil = B64ImageSerializer.convert_itk_to_pil(image_itk)
        image_pil.thumbnail((max_dimension, max_dimension), PILImage.ANTIALIAS)

        decoded_image_pil = PILImage.open(
            BytesIO(b64decode(serializer.data["content"]))
        )

        assert decoded_image_pil.size == image_pil.size
        assert max(decoded_image_pil.size) == max_dimension


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
                    "voxel_width_mm",
                    "voxel_height_mm",
                    "voxel_depth_mm",
                ),
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)
