import pytest

from tests.registrations_tests.factories import OctObsRegistrationFactory


@pytest.mark.django_db
@pytest.mark.parametrize("factory", (OctObsRegistrationFactory,))
def test_factory_creation(factory):
    assert factory()
