import random
import factory
import factory.fuzzy
import datetime
import pytz
from grandchallenge.registrations.models import OctObsRegistration
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.factories import UserFactory
from grandchallenge.retina_images.models import RetinaImage


class OctObsRegistrationFactory(factory.DjangoModelFactory):
    class Meta:
        model = OctObsRegistration

    obs_image = factory.SubFactory(RetinaImageFactory)
    oct_series = factory.SubFactory(RetinaImageFactory)

    registration_values = [
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
    ]
