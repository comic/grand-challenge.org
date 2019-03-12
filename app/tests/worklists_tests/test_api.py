import pytest
from grandchallenge.worklists.serializers import (
    WorklistSerializer,
    WorklistSetSerializer,
)
from tests.worklists_tests.factories import WorklistFactory, WorklistSetFactory
from tests.api_utils import assert_api_crud


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, expected_table, factory, serializer",
    [
        (
            "worklists:lists",
            "Worklist Table",
            WorklistFactory,
            WorklistSerializer,
        ),
        (
            "worklists:sets",
            "Worklist Set Table",
            WorklistSetFactory,
            WorklistSetSerializer,
        ),
    ],
)
def test_api_pages(client, table_reverse, expected_table, factory, serializer):
    assert_api_crud(client, table_reverse, expected_table, factory, serializer)
