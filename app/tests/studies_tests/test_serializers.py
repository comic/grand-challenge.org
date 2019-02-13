import pytest
from tests.serializer_helpers import batch_test_serializers
from tests.studies_tests.factories import StudyFactory
from grandchallenge.studies.serializers import StudySerializer


@pytest.mark.django_db
class TestStudiesSerializers:
    pass


serializers = {
    "study": {
        "unique": True,
        "factory": StudyFactory,
        "serializer": StudySerializer,
        "fields": ("id", "name", "datetime", "patient"),
    }
}

batch_test_serializers(serializers, TestStudiesSerializers)
