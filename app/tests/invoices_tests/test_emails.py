import pytest

from grandchallenge.invoices.emails import get_challenge_invoice_recipients
from tests.factories import UserFactory
from tests.invoices_tests.factories import InvoiceFactory


@pytest.mark.django_db
def test_nonexistent_user_contact_in_recipients():
    contact_email = "contact_person@example.com"

    invoice = InvoiceFactory(
        contact_email=contact_email,
    )

    recipients = get_challenge_invoice_recipients(invoice)

    assert contact_email in [r.email for r in recipients]


@pytest.mark.django_db
def test_existent_user_contact_in_recipients():
    user = UserFactory()

    invoice = InvoiceFactory(
        contact_email=user.email,
    )

    recipients = get_challenge_invoice_recipients(invoice)

    assert user in recipients
