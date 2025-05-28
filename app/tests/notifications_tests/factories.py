import factory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from grandchallenge.notifications.models import Notification
from tests.factories import UserFactory

faker = Faker()

NAMES = [faker.name() for i in range(10)]


class NotificationFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    type = FuzzyChoice(Notification.Type.values)

    class Meta:
        model = Notification
