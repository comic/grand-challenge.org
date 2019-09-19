import random
from PIL import Image as PILImage
import pytest
from django.conf import settings
from django.http import Http404

from grandchallenge.retina_api.serializers import (
    PILImageSerializer,
    BytesImageSerializer,
)
from tests.cases_tests.factories import (
    ImageFactoryWithImageFile,
    ImageFactoryWithoutImageFile,
    ImageFactoryWithImageFile3D,
    ImageFactoryWithImageFile2DLarge,
    ImageFactoryWithImageFile3DLarge3Slices,
    ImageFactoryWithImageFile3DLarge4Slices,
)


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
