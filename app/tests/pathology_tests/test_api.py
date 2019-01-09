import pytest
from tests.factories import (
    PatientItemFactory,
    StudyItemFactory,
    WorklistItemFactory,
)
from tests.api_utils import assert_api_crud


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, record_reverse, expected_table, object_factory",
    [
        (
            "pathology:patient-items",
            "pathology:patient-items",
            "Patient Item Table",
            PatientItemFactory,
        ),
        (
            "pathology:study-items",
            "pathology:study-items",
            "Study Item Table",
            StudyItemFactory,
        ),
        (
            "pathology:worklist-items",
            "pathology:worklist-items",
            "Worklist Item Table",
            WorklistItemFactory,
        ),
    ],
)
def test_api_pages(
    client, table_reverse, record_reverse, expected_table, object_factory
):
    assert_api_crud(
        client, table_reverse, record_reverse, expected_table, object_factory
    )
