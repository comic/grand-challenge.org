from dateutil.relativedelta import relativedelta
from django.core.mail import mail_managers
from django.template.loader import render_to_string
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task

from grandchallenge.invoices.emails import (
    send_challenge_invoice_issued_notification,
    send_challenge_invoice_overdue_reminder,
    send_postpaid_invoice_follow_up_date_approaching_email,
)


@lambda_task
def send_challenge_invoice_overdue_reminder_emails():
    from grandchallenge.invoices.models import Invoice

    invoices_overdue = Invoice.objects.with_overdue_status().filter(
        is_overdue=True
    )
    for invoice in invoices_overdue:
        send_challenge_invoice_overdue_reminder(invoice)


@lambda_task
def send_challenge_invoice_issued_notification_emails(*, pk: int):
    from grandchallenge.invoices.models import Invoice

    invoice = Invoice.objects.get(pk=pk)
    send_challenge_invoice_issued_notification(invoice)


@lambda_task
def send_open_invoices_email():
    from grandchallenge.invoices.models import Invoice

    subject = "Invoices to check"

    post_paid_invoices_to_follow_up = Invoice.objects.filter(
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on__lte=now().date(),
    )
    initialized_prepaid_invoices = Invoice.objects.filter(
        payment_type=Invoice.PaymentTypeChoices.PREPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
    )
    requested_invoices = Invoice.objects.filter(
        payment_status=Invoice.PaymentStatusChoices.REQUESTED,
    )
    issued_invoices = Invoice.objects.filter(
        payment_status=Invoice.PaymentStatusChoices.ISSUED,
    )

    # Only send email if there is at least one invoice in any category
    if not (
        post_paid_invoices_to_follow_up.exists()
        or initialized_prepaid_invoices.exists()
        or requested_invoices.exists()
        or issued_invoices.exists()
    ):
        return

    message = render_to_string(
        "invoices/partials/open_invoices_email.md",
        context={
            "post_paid_invoices_to_follow_up": post_paid_invoices_to_follow_up,
            "initialized_prepaid_invoices": initialized_prepaid_invoices,
            "requested_invoices": requested_invoices,
            "issued_invoices": issued_invoices,
        },
    )

    mail_managers(
        subject=subject,
        message=message,
    )


@lambda_task
def send_post_paid_invoice_follow_up_emails():
    from grandchallenge.invoices.models import Invoice

    invoices = Invoice.objects.filter(
        payment_type=Invoice.PaymentTypeChoices.POSTPAID,
        payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
        follow_up_on__lte=now().date() + relativedelta(months=1, days=1),
    )
    for invoice in invoices:
        send_postpaid_invoice_follow_up_date_approaching_email(invoice)
