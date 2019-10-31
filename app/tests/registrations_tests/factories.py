import factory.fuzzy

from grandchallenge.registrations.models import OctObsRegistration
from tests.cases_tests.factories import ImageFactory
from tests.factories import FuzzyFloatCoordinatesList


class OctObsRegistrationFactory(factory.DjangoModelFactory):
    class Meta:
        model = OctObsRegistration

    obs_image = factory.SubFactory(ImageFactory)
    oct_image = factory.SubFactory(ImageFactory)

    registration_values = FuzzyFloatCoordinatesList(2)
