import pytest
from tests.factories import PatientItemFactory, StudyItemFactory, WorklistItemFactory
from tests.api_utils import assert_api_crud


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, record_reverse, expected_table, object_factory",
    [("pathology:patient_items", "pathology:patient_items", "Patient Item Table", PatientItemFactory),
     ("pathology:study_items", "pathology:study_items", "Study Item Table", StudyItemFactory),
     ("pathology:worklist_items", "pathology:worklist_items", "Worklist Item Table", WorklistItemFactory)],
)
def test_api_pages(client, table_reverse, record_reverse, expected_table, object_factory):
    assert_api_crud(client, table_reverse, record_reverse, expected_table, object_factory)
