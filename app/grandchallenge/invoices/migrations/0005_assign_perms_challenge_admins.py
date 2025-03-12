from django.db import migrations
from guardian.shortcuts import assign_perm


def assign_perms_challenge_admins(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")  # noqa: N806
    for invoice in Invoice.objects.all():
        assign_perm("view_invoice", invoice.challenge.admins_group, invoice)


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0004_alter_invoice_payment_status_and_more"),
    ]

    operations = [
        migrations.RunPython(assign_perms_challenge_admins, elidable=True)
    ]
