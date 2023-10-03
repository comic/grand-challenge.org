import factory

from grandchallenge.invoices.models import Invoice
from tests.factories import ChallengeFactory


class InvoiceFactory(factory.django.DjangoModelFactory):
    challenge = factory.SubFactory(ChallengeFactory)
    support_costs_euros = 0
    compute_costs_euros = 0
    storage_costs_euros = 0

    class Meta:
        model = Invoice
