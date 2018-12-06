import pytest
from tests.datastructures_tests.factories import (
    RetinaImageFactory,
    StudyFactory,
)
from tests.patients_tests.factories import PatientFactory
from tests.archives_tests.factories import ArchiveFactory
from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.studies.serializers import StudySerializer
from grandchallenge.retina_images.serializers import RetinaImageSerializer
from tests.serializer_helpers import batch_test_serializers, check_if_valid


@pytest.mark.django_db
class TestDatastructuresSerializers:
    def test_image_serializer_valid(self):
        assert check_if_valid(RetinaImageFactory(image=None), RetinaImageSerializer)



serializers = {
    "archive": {
        "unique": True,
        "factory": ArchiveFactory,
        "serializer": ArchiveSerializer,
        "fields": ("id", "name", "images"),
    },
    "patient": {
        "unique": True,
        "factory": PatientFactory,
        "serializer": PatientSerializer,
        "fields": ("id", "name"),
    },
    "study": {
        "unique": True,
        "factory": StudyFactory,
        "serializer": StudySerializer,
        "fields": (
            "id",
            "name",
            "datetime",
            "patient",
        ),
    },
    "image": {
        "unique": True,
        "factory": RetinaImageFactory,
        "serializer": RetinaImageSerializer,
        "fields": (
            "id",
            "name",
            "study",
            "number",
            "image",
            "height",
            "width",
            "modality",
            "voxel_size",
            "eye_choice",
        ),
        "no_valid_check": True,  # This check is done manually because of the need to skip the image in the check
    },
}

batch_test_serializers(serializers, TestDatastructuresSerializers)
