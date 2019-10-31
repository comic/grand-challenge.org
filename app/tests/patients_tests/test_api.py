import pytest

from tests.api_utils import assert_api_read_only
from tests.patients_tests.factories import PatientFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, expected_table, user_field, factory",
    [("api:patient-list", "Patient List", "", PatientFactory)],
)
def test_api_pages(client, table_reverse, expected_table, user_field, factory):
    assert_api_read_only(
        client, table_reverse, expected_table, user_field, factory
    )
