from datetime import timedelta

import factory

from grandchallenge.workstations.models import Feedback, SessionCost
from tests.factories import SessionFactory


class FeedbackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Feedback

    session = factory.SubFactory(SessionFactory)
    user_comment = factory.fuzzy.FuzzyText()


class SessionCostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SessionCost

    session = factory.SubFactory(SessionFactory)
    duration = timedelta(minutes=15)
