import factory
from tests.factories import UserFactory
from grandchallenge.worklists.models import Worklist, WorklistSet


class WorklistSetFactory(factory.DjangoModelFactory):
    class Meta:
        model = WorklistSet

    title = factory.Sequence(lambda n: f"worklist_set_{n}")
    user = factory.SubFactory(UserFactory)


class WorklistFactory(factory.DjangoModelFactory):
    class Meta:
        model = Worklist

    title = factory.Sequence(lambda n: f"worklist_{n}")
    set = factory.SubFactory(WorklistSetFactory)
