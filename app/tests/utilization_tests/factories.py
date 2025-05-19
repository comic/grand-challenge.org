from datetime import timedelta

import factory

from grandchallenge.utilization.models import SessionCost
from tests.factories import SessionFactory


class SessionCostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SessionCost

    session = factory.SubFactory(SessionFactory)
    duration = timedelta(minutes=15)
