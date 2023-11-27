import factory

from grandchallenge.incentives.models import Incentive


class IncentiveFactory(factory.django.DjangoModelFactory):
    incentive = factory.Sequence(lambda n: f"Incentive {n}")

    class Meta:
        model = Incentive
