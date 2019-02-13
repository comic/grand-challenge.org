import pytest
from tests.registrations_tests.factories import OctObsRegistrationFactory
from tests.model_helpers import batch_test_factories


@pytest.mark.django_db
class TestRegistrationModels:
    # test functions are added dynamically to this class
    pass


factories = {"octobsregistration": OctObsRegistrationFactory}
batch_test_factories(factories, TestRegistrationModels)
