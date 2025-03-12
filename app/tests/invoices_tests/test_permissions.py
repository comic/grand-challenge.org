import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from guardian.shortcuts import get_perms

from tests.invoices_tests.factories import InvoiceFactory


@pytest.mark.django_db
def test_invoice_permissions():
    invoice = InvoiceFactory()

    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    reg_anon_perms = get_perms(g_reg_anon, invoice)
    assert "view_invoice" not in reg_anon_perms
    assert "change_invoice" not in reg_anon_perms

    reg_perms = get_perms(g_reg, invoice)
    assert "view_invoice" not in reg_perms
    assert "change_invoice" not in reg_perms

    participants_perms = get_perms(
        invoice.challenge.participants_group, invoice
    )
    assert "view_invoice" not in participants_perms
    assert "change_invoice" not in participants_perms

    admins_perms = get_perms(invoice.challenge.admins_group, invoice)
    assert "view_invoice" in admins_perms
    assert "change_invoice" not in admins_perms
