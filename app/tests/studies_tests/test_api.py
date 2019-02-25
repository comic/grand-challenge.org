import pytest
from tests.studies_tests.factories import StudyFactory
from tests.api_utils import assert_api_crud


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, expected_table, object_factory",
    [("studies:studies", "Study Table", StudyFactory)],
)
def test_api_pages(
    client, table_reverse, expected_table, object_factory
):
    assert_api_crud(
        client, table_reverse, expected_table, object_factory
    )
