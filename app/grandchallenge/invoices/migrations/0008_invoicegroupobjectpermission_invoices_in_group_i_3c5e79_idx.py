# Generated by Django 4.2.20 on 2025-05-14 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0007_alter_invoice_billing_address_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="invoicegroupobjectpermission",
            index=models.Index(
                fields=["group", "permission"],
                name="invoices_in_group_i_3c5e79_idx",
            ),
        ),
    ]
