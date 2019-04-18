import pytest
from tests.studies_tests.factories import StudyFactory
from tests.api_utils import assert_api_read_only


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, expected_table, factory",
    [("api:study", "Study Table", StudyFactory)],
)
def test_api_pages(client, table_reverse, expected_table, factory):
    assert_api_read_only(client, table_reverse, expected_table, factory)
