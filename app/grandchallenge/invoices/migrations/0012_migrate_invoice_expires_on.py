from datetime import timedelta

from django.conf import settings
from django.db import migrations
from django.db.models import DateField, ExpressionWrapper, F
from django.db.models.functions import TruncDate


def set_expires_on(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")  # noqa: N806
    Invoice.objects.update(
        expires_on=ExpressionWrapper(
            TruncDate(F("created"))
            + timedelta(
                days=365
                * settings.CHALLENGE_INVOICES_DEFAULT_EXPIRE_AFTER_YEARS
            ),
            output_field=DateField(),
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "invoices",
            "0011_invoice_expires_on",
        ),
    ]

    operations = [
        migrations.RunPython(set_expires_on, elidable=True),
    ]
