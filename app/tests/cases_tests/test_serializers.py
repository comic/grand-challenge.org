import pytest

from grandchallenge.cases.serializers import ImageSerializer
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.serializer_helpers import (
    check_if_valid,
    do_test_serializer_fields,
    do_test_serializer_valid,
)


@pytest.mark.django_db
class TestRetinaImageSerializers:
    def test_image_serializer_valid(self):
        assert check_if_valid(ImageFactoryWithImageFile(), ImageSerializer)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "serializer_data",
    (
        (
            {
                "unique": True,
                "factory": ImageFactoryWithImageFile,
                "serializer": ImageSerializer,
                "fields": (
                    "pk",
                    "name",
                    "study",
                    "files",
                    "width",
                    "height",
                    "depth",
                    "color_space",
                    "modality",
                    "eye_choice",
                    "stereoscopic_choice",
                    "field_of_view",
                    "shape_without_color",
                    "shape",
                    "voxel_width_mm",
                    "voxel_height_mm",
                    "voxel_depth_mm",
                ),
                "no_valid_check": True,
                # This check is done manually because of the need to skip the image in the check
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data):
        do_test_serializer_valid(serializer_data)

    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)
