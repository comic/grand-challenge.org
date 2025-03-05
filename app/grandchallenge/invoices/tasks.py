from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.invoices.emails import (
    send_challenge_invoice_issued_notification,
    send_challenge_outstanding_invoice_alert,
)


@acks_late_micro_short_task
@transaction.atomic
def send_challenge_invoice_reminder_emails():
    from grandchallenge.invoices.models import Invoice

    _now = now()
    outstanding_invoices = Invoice.objects.filter(
        payment_type__in=[
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentTypeChoices.POSTPAID,
        ],
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
        issued_on__lt=_now - settings.CHALLENGE_INVOICE_OUTSTANDING_CUTOFF,
    )
    for invoice in outstanding_invoices:
        send_challenge_outstanding_invoice_alert(invoice)


@acks_late_micro_short_task
@transaction.atomic
def send_challenge_invoice_issued_emails(*, pk):
    from grandchallenge.invoices.models import Invoice

    invoice = Invoice.objects.get(pk=pk)
    send_challenge_invoice_issued_notification(invoice)
