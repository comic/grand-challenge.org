from collections import namedtuple

from django.contrib.sites.models import Site
from django.core.mail import mail_managers
from django.template.loader import render_to_string
from django.utils.html import format_html

from grandchallenge.emails.emails import send_standard_email_batch
from grandchallenge.profiles.models import EmailSubscriptionTypes


def get_challenge_invoice_recipients(invoice):
    recipients = [*invoice.challenge.get_admins()]

    if invoice.contact_email:
        username = (
            invoice.contact_name
            if invoice.contact_name
            else invoice.contact_email
        )
        user_profile = namedtuple("UserProfile", ["get_unsubscribe_link"])(
            get_unsubscribe_link=lambda *_, **__: None
        )
        contact_user = namedtuple(
            "User", ["username", "email", "user_profile"]
        )(
            username=username,
            email=invoice.contact_email,
            user_profile=user_profile,
        )
        recipients.append(contact_user)

    return recipients


def send_challenge_outstanding_invoice_reminder(invoice):
    subject = format_html(
        "[{challenge_name}] Outstanding Invoice Reminder",
        challenge_name=invoice.challenge.short_name,
    )
    challenge_admins_message = render_to_string(
        "invoices/partials/challenge_outstanding_invoice_reminder_email.md",
        context={
            "invoice": invoice,
        },
    )
    challenge_admins_recipients = get_challenge_invoice_recipients(invoice)

    send_standard_email_batch(
        site=Site.objects.get_current(),
        subject=subject,
        markdown_message=challenge_admins_message,
        recipients=challenge_admins_recipients,
        subscription_type=EmailSubscriptionTypes.SYSTEM,
    )

    managers_message = format_html(
        "An invoice alert has been sent for the {challenge_name} challenge regarding "
        "the invoice issued on {issued_on}.",
        challenge_name=invoice.challenge.short_name,
        issued_on=invoice.issued_on,
    )
    mail_managers(
        subject=subject,
        message=managers_message,
    )


def send_challenge_invoice_issued_notification(invoice):
    subject = format_html(
        "[{challenge_name}] Invoice Issued Notification",
        challenge_name=invoice.challenge.short_name,
    )
    message = render_to_string(
        "invoices/partials/challenge_invoice_issued_notification_email.md",
        context={
            "invoice": invoice,
        },
    )
    recipients = get_challenge_invoice_recipients(invoice)

    send_standard_email_batch(
        site=Site.objects.get_current(),
        subject=subject,
        markdown_message=message,
        recipients=recipients,
        subscription_type=EmailSubscriptionTypes.SYSTEM,
    )
