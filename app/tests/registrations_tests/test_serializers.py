import pytest

from grandchallenge.registrations.serializers import (
    OctObsRegistrationSerializer,
)
from tests.registrations_tests.factories import OctObsRegistrationFactory
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
                "factory": OctObsRegistrationFactory,
                "serializer": OctObsRegistrationSerializer,
                "fields": ("obs_image", "oct_image", "registration_values"),
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data):
        do_test_serializer_valid(serializer_data)

    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)
