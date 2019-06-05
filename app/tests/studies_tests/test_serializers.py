import pytest
from tests.serializer_helpers import (
    do_test_serializer_valid,
    do_test_serializer_fields,
)
from tests.studies_tests.factories import StudyFactory
from grandchallenge.studies.serializers import StudySerializer


@pytest.mark.django_db
@pytest.mark.parametrize(
    "serializer_data",
    (
        (
            {
                "unique": True,
                "factory": StudyFactory,
                "serializer": StudySerializer,
                "fields": ("id", "name", "datetime", "patient"),
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data):
        do_test_serializer_valid(serializer_data)

    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)
