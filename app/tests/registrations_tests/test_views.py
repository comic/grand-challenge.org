import pytest
from tests.registrations_tests.factories import OctObsRegistrationFactory
from tests.retina_images_tests.factories import ImageFactory
from tests.factories import UserFactory
from grandchallenge.registrations.views import OctObsRegistrationViewSet
from grandchallenge.registrations.serializers import (
    OctObsRegistrationSerializer
)
from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS


@pytest.mark.django_db
class TestViewsets:
    # test functions are added dynamically to this class
    pass


actions = VIEWSET_ACTIONS
# Add all model viewset test functions to class
required_relations = {"obs_image": ImageFactory, "oct_series": ImageFactory}
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
