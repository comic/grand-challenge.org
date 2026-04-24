from datetime import timedelta

from django.conf import settings
from django.db import migrations, models


def set_expires_on(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")  # noqa: N806
    for invoice in Invoice.objects.filter(expires_on__isnull=True):
        invoice.expires_on = invoice.created + timedelta(
            days=365 * settings.CHALLENGE_INVOICES_EXPIRE_AFTER_YEARS
        )
        invoice.save(update_fields=["expires_on"])


class Migration(migrations.Migration):

    dependencies = [
        (
            "invoices",
            "0010_invoiceuserobjectpermission_invoices_in_user_id_66e98c_idx",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="expires_on",
            field=models.DateField(
                help_text="The date when the invoice expires", null=True
            ),
        ),
        migrations.RunPython(set_expires_on, elidable=True),
        migrations.AlterField(
            model_name="invoice",
            name="expires_on",
            field=models.DateField(
                help_text="The date when the invoice expires"
            ),
        ),
    ]
