import pytest

from grandchallenge.registrations.serializers import (
    OctObsRegistrationSerializer,
)
from grandchallenge.registrations.views import OctObsRegistrationViewSet
from tests.cases_tests.factories import ImageFactory
from tests.registrations_tests.factories import OctObsRegistrationFactory
from tests.viewset_helpers import VIEWSET_ACTIONS, batch_test_viewset_endpoints


@pytest.mark.django_db
class TestViewsets:
    # test functions are added dynamically to this class
    pass


actions = VIEWSET_ACTIONS
# Add all model viewset test functions to class
required_relations = {"obs_image": ImageFactory, "oct_image": ImageFactory}
batch_test_viewset_endpoints(
    actions,
    OctObsRegistrationViewSet,
    "octobsregistration",
    "registrations",
    OctObsRegistrationFactory,
    TestViewsets,
    required_relations,
    serializer=OctObsRegistrationSerializer,
)
