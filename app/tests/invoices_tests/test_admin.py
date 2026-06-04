import datetime

import pytest
from django.contrib.admin import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

from grandchallenge.invoices.admin import InvoiceAdmin
from grandchallenge.invoices.models import Invoice
from tests.factories import ChallengeFactory
from tests.invoices_tests.factories import InvoiceFactory


@pytest.mark.django_db
def test_calculate_postpaid_costs(rf):
    challenge = ChallengeFactory(
        compute_cost_euro_millicents=300 * 100_000,  # €300
        size_in_storage=1024**3 * 30,  # 30 GB
        size_in_registry=1024**3 * 70,  # 70 GB
    )  # Incurred: 67 Euro storage, 300 Euro compute

    # Prepaid invoice covers part of the budget
    InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.COMPLIMENTARY,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        compute_costs_euros=150,
        storage_costs_euros=20,
        support_costs_euros=0,
        internal_comments="comment",
    )

    invoice = InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        billing_address="test",
        contact_email="e@e.com",
        contact_name="John",
        follow_up_on=datetime.datetime.now(),
        vat_number="1234",
        support_costs_euros=0,
        compute_costs_euros=0,
        storage_costs_euros=0,
        compute_cost_euro_millicents=150 * 100_000,
    )

    modeladmin = InvoiceAdmin(invoice, AdminSite)
    request = rf.get("/foo")

    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    # Add messages storage
    messages_storage = FallbackStorage(request)
    request.session["_messages"] = messages_storage
    request._messages = messages_storage

    modeladmin.calculate_postpaid_costs(
        request=request, queryset=Invoice.objects.filter(pk=invoice.pk)
    )

    invoice.refresh_from_db()
    assert invoice.compute_costs_euros == 187
    assert invoice.storage_costs_euros == 63
    # Rounded to nearest 250 increment
    assert (
        invoice.compute_costs_euros + invoice.storage_costs_euros
    ) % 250 == 0

    stored_messages = [m.message for m in request._messages]

    assert any(
        f"1 postpaid invoice was updated: {invoice.pk}" in message
        for message in stored_messages
    )


@pytest.mark.parametrize(
    "payment_type, payment_status",
    [
        (
            Invoice.PaymentTypeChoices.COMPLIMENTARY,
            Invoice.PaymentStatusChoices.PAID,
        ),
        (
            Invoice.PaymentTypeChoices.COMPLIMENTARY,
            Invoice.PaymentStatusChoices.ISSUED,
        ),
        (
            Invoice.PaymentTypeChoices.COMPLIMENTARY,
            Invoice.PaymentStatusChoices.INITIALIZED,
        ),
        (
            Invoice.PaymentTypeChoices.COMPLIMENTARY,
            Invoice.PaymentStatusChoices.CANCELLED,
        ),
        (
            Invoice.PaymentTypeChoices.COMPLIMENTARY,
            Invoice.PaymentStatusChoices.REQUESTED,
        ),
        (
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentStatusChoices.PAID,
        ),
        (
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentStatusChoices.ISSUED,
        ),
        (
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentStatusChoices.INITIALIZED,
        ),
        (
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentStatusChoices.CANCELLED,
        ),
        (
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentStatusChoices.REQUESTED,
        ),
        (
            Invoice.PaymentTypeChoices.POSTPAID,
            Invoice.PaymentStatusChoices.PAID,
        ),
        (
            Invoice.PaymentTypeChoices.POSTPAID,
            Invoice.PaymentStatusChoices.ISSUED,
        ),
        (
            Invoice.PaymentTypeChoices.POSTPAID,
            Invoice.PaymentStatusChoices.CANCELLED,
        ),
        (
            Invoice.PaymentTypeChoices.POSTPAID,
            Invoice.PaymentStatusChoices.REQUESTED,
        ),
    ],
)
@pytest.mark.django_db
def test_calculate_postpaid_costs_status_filter(
    rf, payment_type, payment_status
):
    inv = InvoiceFactory(
        payment_status=payment_status,
        payment_type=payment_type,
        compute_costs_euros=123,
        storage_costs_euros=456,
    )
    modeladmin = InvoiceAdmin(inv, AdminSite)
    request = rf.get("/foo")

    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    # Add messages storage
    messages_storage = FallbackStorage(request)
    request.session["_messages"] = messages_storage
    request._messages = messages_storage

    modeladmin.calculate_postpaid_costs(
        request=request, queryset=Invoice.objects.all()
    )

    stored_messages = [m.message for m in request._messages]

    assert any(
        "1 invoice was skipped because it's not POSTPAID and INITIALIZED."
        in message
        for message in stored_messages
    )

    # costs have not been updated
    inv.refresh_from_db()
    assert inv.compute_costs_euros == 123
    assert inv.storage_costs_euros == 456


@pytest.mark.django_db
def test_calculate_postpaid_costs_challenge_filter(rf):
    challenge = ChallengeFactory()
    inv1, inv2 = InvoiceFactory.create_batch(
        2,
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        compute_costs_euros=123,
        storage_costs_euros=456,
    )
    modeladmin = InvoiceAdmin(inv1, AdminSite)
    request = rf.get("/foo")

    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    # Add messages storage
    messages_storage = FallbackStorage(request)
    request.session["_messages"] = messages_storage
    request._messages = messages_storage

    modeladmin.calculate_postpaid_costs(
        request=request, queryset=Invoice.objects.all()
    )

    stored_messages = [m.message for m in request._messages]

    assert any(
        "You can only update one invoice per challenge at a time. Aborting action."
        in message
        for message in stored_messages
    )


@pytest.mark.django_db
def test_calculate_postpaid_costs_unused_budget(rf):
    challenge = ChallengeFactory(
        compute_cost_euro_millicents=10 * 100_000,  # €10
        size_in_storage=1024**3 * 3,  # 3 GB
        size_in_registry=1024**3 * 7,  # 7 GB
    )  # Incurred: x Euro storage, 10 Euro compute

    # Prepaid invoice covers the costs
    InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.PAID,
        compute_costs_euros=150,
        storage_costs_euros=20,
        support_costs_euros=0,
        internal_comments="comment",
    )

    invoice = InvoiceFactory(
        challenge=challenge,
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        billing_address="test",
        contact_email="e@e.com",
        contact_name="John",
        follow_up_on=datetime.datetime.now(),
        vat_number="1234",
        support_costs_euros=0,
        compute_costs_euros=0,
        storage_costs_euros=0,
    )

    modeladmin = InvoiceAdmin(invoice, AdminSite)
    request = rf.get("/foo")

    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    # Add messages storage
    messages_storage = FallbackStorage(request)
    request.session["_messages"] = messages_storage
    request._messages = messages_storage

    modeladmin.calculate_postpaid_costs(
        request=request, queryset=Invoice.objects.filter(pk=invoice.pk)
    )

    invoice.refresh_from_db()
    assert invoice.compute_costs_euros == 0
    assert invoice.storage_costs_euros == 0

    stored_messages = [m.message for m in request._messages]

    assert any(
        f"1 invoice was skipped as its postpaid budget has not been used: {invoice.pk}"
        in message
        for message in stored_messages
    )
