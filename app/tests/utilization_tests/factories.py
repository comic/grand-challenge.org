from datetime import timedelta

import factory

from grandchallenge.utilization.models import SessionUtilization
from tests.factories import SessionFactory


class SessionUtilizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SessionUtilization

    session = factory.SubFactory(SessionFactory)
    duration = timedelta(minutes=15)
