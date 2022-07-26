import factory

from grandchallenge.workstations.models import Feedback
from tests.factories import SessionFactory


class FeedbackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Feedback

    session = factory.SubFactory(SessionFactory)
    user_comment = factory.fuzzy.FuzzyText()
