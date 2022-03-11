import factory
from faker import Faker

from grandchallenge.hanging_protocols.models import HangingProtocol
from tests.factories import UserFactory

faker = Faker()


class HangingProtocolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HangingProtocol

    title = factory.LazyAttribute(lambda t: faker.text(max_nb_chars=10))
    description = factory.LazyAttribute(lambda t: faker.text(max_nb_chars=200))
    creator = factory.SubFactory(UserFactory)
    json = factory.LazyAttribute(lambda t: faker.text(max_nb_chars=10))
