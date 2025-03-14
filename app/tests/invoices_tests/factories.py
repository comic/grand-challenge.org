import factory

from grandchallenge.invoices.models import Invoice
from tests.factories import ChallengeFactory


class InvoiceFactory(factory.django.DjangoModelFactory):
    challenge = factory.SubFactory(ChallengeFactory)
    support_costs_euros = 0
    compute_costs_euros = 0
    storage_costs_euros = 0
    internal_comments = factory.Faker("text")
    contact_name = factory.Faker("name")
    contact_email = factory.Faker("email")
    billing_address = factory.Faker("address")
    vat_number = factory.Faker("vin")

    class Meta:
        model = Invoice
