import pytest
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.studies_tests.factories import StudyFactory
from tests.patients_tests.factories import PatientFactory
from tests.archives_tests.factories import ArchiveFactory
from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.studies.serializers import StudySerializer
from grandchallenge.retina_images.serializers import RetinaImageSerializer
from tests.serializer_helpers import batch_test_serializers


@pytest.mark.django_db
class TestDatastructuresSerializers:
    pass



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
}

batch_test_serializers(serializers, TestDatastructuresSerializers)
