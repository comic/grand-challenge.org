import pytest
from grandchallenge.patients.serializers import PatientSerializer
from tests.patients_tests.factories import PatientFactory
from tests.api_utils import assert_api_crud


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, expected_table, factory, serializer",
    [
        (
            "patients:patients",
            "Patient Table",
            PatientFactory,
            PatientSerializer,
        )
    ],
)
def test_api_pages(client, table_reverse, expected_table, factory, serializer):
    assert_api_crud(client, table_reverse, expected_table, factory, serializer)
