import pytest
from grandchallenge.cases.serializers import ImageSerializer
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.serializer_helpers import check_if_valid
from tests.serializer_helpers import batch_test_serializers


@pytest.mark.django_db
class TestRetinaImageSerializers:
    def test_image_serializer_valid(self):
        assert check_if_valid(ImageFactoryWithImageFile(), ImageSerializer)


serializers = {
    "image": {
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
            "cirrus_link",
        ),
        "no_valid_check": True,  # This check is done manually because of the need to skip the image in the check
    }
}

batch_test_serializers(serializers, TestRetinaImageSerializers)
