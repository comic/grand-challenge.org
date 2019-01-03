import random
import factory.fuzzy
from grandchallenge.registrations.models import OctObsRegistration
from tests.cases_tests.factories import ImageFactory


class OctObsRegistrationFactory(factory.DjangoModelFactory):
    class Meta:
        model = OctObsRegistration

    obs_image = factory.SubFactory(ImageFactory)
    oct_image = factory.SubFactory(ImageFactory)

    registration_values = [
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
    ]
