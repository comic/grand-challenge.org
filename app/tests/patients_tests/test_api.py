import pytest
from tests.patients_tests.factories import PatientFactory
from tests.api_utils import assert_api_crud


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, record_reverse, expected_table, object_factory",
    [("patients:patients", "Patient Table", PatientFactory)],
)
def test_api_pages(
    client, table_reverse, expected_table, object_factory
):
    assert_api_crud(
        client, table_reverse, expected_table, object_factory
    )
