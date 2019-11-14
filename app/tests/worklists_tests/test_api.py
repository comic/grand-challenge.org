import pytest

from tests.api_utils import assert_api_crud
from tests.worklists_tests.factories import WorklistFactory


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
