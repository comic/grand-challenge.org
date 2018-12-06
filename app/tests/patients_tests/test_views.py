import pytest
from grandchallenge.patients.views import PatientViewSet
from tests.patients_tests.factories import PatientFactory
from grandchallenge.patients.serializers import PatientSerializer
from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS


@pytest.mark.django_db
class TestViewsets:
    # test functions are added dynamically to this class
    pass


batch_test_viewset_endpoints(
    VIEWSET_ACTIONS,
    PatientViewSet,
    "patient",
    PatientFactory,
    TestViewsets,
    # required_relations,
    serializer=PatientSerializer,
)
