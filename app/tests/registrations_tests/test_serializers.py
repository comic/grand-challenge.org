import pytest
from tests.registrations_tests.factories import OctObsRegistrationFactory
from grandchallenge.registrations.serializers import OctObsRegistrationSerializer
from tests.serializer_helpers import batch_test_serializers


@pytest.mark.django_db
class TestRegistrationSerializers:
    # test methods are added dynamically to this class, see below
    pass


serializers = {
    "octobsregistration": {
        "unique": True,
        "factory": OctObsRegistrationFactory,
        "serializer": OctObsRegistrationSerializer,
        "fields": ("obs_image", "oct_series", "registration_values"),
    }
}

batch_test_serializers(serializers, TestRegistrationSerializers)
