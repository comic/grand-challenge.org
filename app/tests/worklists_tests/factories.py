import factory
from grandchallenge.worklists.models import Worklist


class WorklistFactory(factory.DjangoModelFactory):
    class Meta:
        model = Worklist

    title = factory.Sequence(lambda n: f"worklist_{n}")
    user = None
