import pytest
from guardian.shortcuts import get_users_with_perms

from tests.evaluation_tests.test_permissions import get_groups_with_set_perms
from tests.invoices_tests.factories import InvoiceFactory


@pytest.mark.django_db
def test_invoice_permissions():
    invoice = InvoiceFactory()

    assert get_groups_with_set_perms(invoice) == {
        invoice.challenge.admins_group: {"view_invoice"},
    }
    assert get_users_with_perms(invoice, with_group_users=False).count() == 0
