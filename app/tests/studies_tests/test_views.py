import pytest
from tests.patients_tests.factories import PatientFactory
from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS
from grandchallenge.studies.serializers import StudySerializer
from grandchallenge.studies.views import StudyViewSet
from tests.studies_tests.factories import StudyFactory


@pytest.mark.django_db
class TestViewsets:
    # test functions are added dynamically to this class
    pass


required_relations = {"patient": PatientFactory}
batch_test_viewset_endpoints(
    VIEWSET_ACTIONS,
    StudyViewSet,
    "study",
    "studies",
    StudyFactory,
    TestViewsets,
    required_relations,
    serializer=StudySerializer,
)
