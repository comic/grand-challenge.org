from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.invoices.emails import (
    send_challenge_invoice_issued_notification,
    send_challenge_invoice_overdue_reminder,
)


@acks_late_2xlarge_task
@transaction.atomic
def send_challenge_invoice_overdue_reminder_emails():
    from grandchallenge.invoices.models import Invoice

    _now = now()
    invoices_overdue = Invoice.objects.filter(
        payment_type__in=[
            Invoice.PaymentTypeChoices.PREPAID,
            Invoice.PaymentTypeChoices.POSTPAID,
        ],
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
        issued_on__lt=_now - settings.CHALLENGE_INVOICE_OVERDUE_CUTOFF,
    )
    for invoice in invoices_overdue:
        send_challenge_invoice_overdue_reminder(invoice)


@acks_late_micro_short_task
@transaction.atomic
def send_challenge_invoice_issued_notification_emails(*, pk):
    from grandchallenge.invoices.models import Invoice

    invoice = Invoice.objects.get(pk=pk)
    send_challenge_invoice_issued_notification(invoice)
