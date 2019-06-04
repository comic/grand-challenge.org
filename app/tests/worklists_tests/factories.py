import factory

from grandchallenge.worklists.models import Worklist
from tests.factories import UserFactory


class WorklistFactory(factory.DjangoModelFactory):
    class Meta:
        model = Worklist

    title = factory.Sequence(lambda n: f"worklist_{n}")
    creator = factory.SubFactory(UserFactory)
