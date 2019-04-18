import factory
from tests.factories import UserFactory
from grandchallenge.worklists.models import Worklist


class WorklistFactory(factory.DjangoModelFactory):
    class Meta:
        model = Worklist

    title = factory.Sequence(lambda n: f"worklist_{n}")
    user = factory.SubFactory(UserFactory)
