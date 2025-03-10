from django.db import migrations

from grandchallenge.invoices.models import (
    PaymentStatusChoices,
    PaymentTypeChoices,
)


def move_complimentary_status_to_type(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")  # noqa: N806
    for invoice in Invoice.objects.filter(payment_status="COMPLIMENTARY"):
        invoice.payment_type = PaymentTypeChoices.COMPLIMENTARY
        invoice.payment_status = PaymentStatusChoices.PAID
        invoice.save()


class Migration(migrations.Migration):
    dependencies = [
        (
            "invoices",
            "0002_invoice_payment_type_alter_invoice_payment_status_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(move_complimentary_status_to_type, elidable=True)
    ]
