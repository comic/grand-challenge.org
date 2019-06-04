import pytest
from tests.worklists_tests.factories import WorklistFactory
from tests.api_utils import assert_api_crud


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, expected_table, factory, user_field, invalid_fields",
    [("api:worklist-list", "Worklist List", WorklistFactory, "creator", [])],
)
def test_api_pages(
    client, table_reverse, expected_table, factory, user_field, invalid_fields
):
    assert_api_crud(
        client,
        table_reverse,
        expected_table,
        factory,
        user_field,
        invalid_fields,
    )
