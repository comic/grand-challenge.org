from datetime import timedelta

import factory
from dateutil.utils import today

from grandchallenge.invoices.models import Invoice
from tests.factories import ChallengeFactory


class InvoiceFactory(factory.django.DjangoModelFactory):
    challenge = factory.SubFactory(ChallengeFactory)
    payment_type = Invoice.PaymentTypeChoices.PREPAID
    payment_status = Invoice.PaymentStatusChoices.PAID
    support_costs_euros = 100
    compute_costs_euros = 100
    storage_costs_euros = 100
    issued_on = factory.Faker("past_date")
    paid_on = factory.Faker("past_date")
    internal_invoice_number = factory.Faker("numerify", text="#########")
    internal_client_number = factory.Faker("bothify", text="H######")
    internal_comments = factory.Faker("text")
    contact_name = factory.Faker("name")
    contact_email = factory.Faker("email")
    billing_address = factory.Faker("address")
    vat_number = factory.Faker("vin")
    follow_up_on = factory.LazyAttribute(
        lambda o: (
            today() + timedelta(days=30)
            if o.payment_type == Invoice.PaymentTypeChoices.POSTPAID
            else None
        )
    )

    class Meta:
        model = Invoice
