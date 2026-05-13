from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils.timezone import now

from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.invoices.emails import (
    send_challenge_invoice_issued_notification,
    send_challenge_invoice_overdue_reminder,
    send_postpaid_invoice_follow_up_date_approaching_email,
)


@acks_late_2xlarge_task
@transaction.atomic
def send_challenge_invoice_overdue_reminder_emails():
    from grandchallenge.invoices.models import Invoice

    invoices_overdue = Invoice.objects.with_overdue_status().filter(
        is_overdue=True
    )
    for invoice in invoices_overdue:
        send_challenge_invoice_overdue_reminder(invoice)


@acks_late_micro_short_task
@transaction.atomic
def send_challenge_invoice_issued_notification_emails(*, pk):
    from grandchallenge.invoices.models import Invoice

    invoice = Invoice.objects.get(pk=pk)
    send_challenge_invoice_issued_notification(invoice)


@acks_late_micro_short_task
@transaction.atomic
def send_post_paid_invoice_follow_up_emails():
    from grandchallenge.invoices.models import Invoice

    invoices = Invoice.objects.filter(
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on__lte=now().date() + relativedelta(months=1, days=1),
    )
    for invoice in invoices:
        send_postpaid_invoice_follow_up_date_approaching_email(invoice)
