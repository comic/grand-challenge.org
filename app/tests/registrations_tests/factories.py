import random
import factory
import factory.fuzzy
import datetime
import pytz
from grandchallenge.registrations.models import OctObsRegistration
from grandchallenge.challenges.models import ImagingModality
from tests.retina_images_tests.factories import ImageFactory
from tests.factories import UserFactory


class OctObsRegistrationFactory(factory.DjangoModelFactory):
    class Meta:
        model = OctObsRegistration

    obs_image = factory.SubFactory(ImageFactory)
    oct_image = factory.SubFactory(ImageFactory)

    registration_values = [
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
    ]
