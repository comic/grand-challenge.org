import pytest
from tests.factories import WorklistFactory, WorklistSetFactory
from tests.api_utils import assert_api_crud


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, record_reverse, expected_table, object_factory",
    [("worklists:worklists", "worklists:worklists", "Worklist Table", WorklistFactory),
     ("worklists:sets", "worklists:sets", "Worklist Set Table", WorklistSetFactory)],
)
def test_api_pages(client, table_reverse, record_reverse, expected_table, object_factory):
    assert_api_crud(client, table_reverse, record_reverse, expected_table, object_factory)
