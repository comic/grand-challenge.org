import pytest
from tests.serializer_helpers import batch_test_serializers
from grandchallenge.patients.serializers import PatientSerializer
from tests.patients_tests.factories import PatientFactory


@pytest.mark.django_db
class TestPatientsSerializers:
    pass


serializers = {
    "patient": {
        "unique": True,
        "factory": PatientFactory,
        "serializer": PatientSerializer,
        "fields": ("id", "name"),
    },
}

batch_test_serializers(serializers, TestPatientsSerializers)
