import pytest
from grandchallenge.retina_images.serializers import RetinaImageSerializer
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.serializer_helpers import check_if_valid
from tests.serializer_helpers import batch_test_serializers

@pytest.mark.django_db
class TestRetinaImageSerializers:
    def test_image_serializer_valid(self):
        assert check_if_valid(RetinaImageFactory(image=None), RetinaImageSerializer)


serializers = {
    "image": {
        "unique": True,
        "factory": RetinaImageFactory,
        "serializer": RetinaImageSerializer,
        "fields": (
            "id",
            "name",
            "study",
            "image",
            "modality",
            "voxel_size",
            "eye_choice",
        ),
        "no_valid_check": True,  # This check is done manually because of the need to skip the image in the check
    },
}

batch_test_serializers(serializers, TestRetinaImageSerializers)
