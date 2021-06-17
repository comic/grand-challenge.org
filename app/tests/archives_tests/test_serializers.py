import pytest

from grandchallenge.archives.serializers import ArchiveSerializer
from tests.archives_tests.factories import ArchiveFactory
from tests.serializer_helpers import (
    do_test_serializer_fields,
    do_test_serializer_valid,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "serializer_data",
    (
        (
            {
                "unique": True,
                "factory": ArchiveFactory,
                "serializer": ArchiveSerializer,
                "fields": (
                    "id",
                    "name",
                    "title",
                    "api_url",
                    "url",
                    "algorithms",
                    "logo",
                    "description",
                ),
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data, rf):
        do_test_serializer_valid(serializer_data, request=rf.get("/foo"))

    def test_serializer_fields(self, serializer_data, rf):
        do_test_serializer_fields(serializer_data, request=rf.get("/foo"))
