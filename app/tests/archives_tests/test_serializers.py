import pytest
from tests.archives_tests.factories import ArchiveFactory
from grandchallenge.archives.serializers import ArchiveSerializer
from tests.serializer_helpers import batch_test_serializers


@pytest.mark.django_db
class TestArchivesSerializers:
    pass


serializers = {
    "archive": {
        "unique": True,
        "factory": ArchiveFactory,
        "serializer": ArchiveSerializer,
        "fields": ("id", "name", "images"),
    },
}

batch_test_serializers(serializers, TestArchivesSerializers)
