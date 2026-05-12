from datetime import timedelta

import factory
from dateutil.utils import today

from grandchallenge.invoices.models import Invoice
from tests.factories import ChallengeFactory


class InvoiceFactory(factory.django.DjangoModelFactory):
    challenge = factory.SubFactory(ChallengeFactory)
    payment_type = Invoice.PaymentTypeChoices.PREPAID
    support_costs_euros = 0
    compute_costs_euros = 0
    storage_costs_euros = 0
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

    @classmethod
    def create_valid(cls, **kwargs):
        invoice = cls.create(**kwargs)
        if "support_costs_euros" not in kwargs:
            invoice.support_costs_euros = 100
        if "compute_costs_euros" not in kwargs:
            invoice.compute_costs_euros = 100
        if "storage_costs_euros" not in kwargs:
            invoice.storage_costs_euros = 100
        if "payment_type" not in kwargs:
            invoice.payment_type = Invoice.PaymentTypeChoices.PREPAID
        if "payment_status" not in kwargs:
            invoice.payment_status = Invoice.PaymentStatusChoices.PAID
        invoice.save()
        return invoice

    class Meta:
        model = Invoice
