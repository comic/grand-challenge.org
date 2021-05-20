import pytest

from tests.registrations_tests.factories import OctObsRegistrationFactory


@pytest.mark.django_db
class TestRegistrationModels:
    # test functions are added dynamically to this class
    pass


@pytest.mark.django_db
@pytest.mark.parametrize("factory", (OctObsRegistrationFactory,))
class TestFactories:
    def test_factory_creation(self, factory):
        assert factory()
