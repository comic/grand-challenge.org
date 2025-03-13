from django.db import migrations


def assign_perms_challenge_admins(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")  # noqa: N806
    InvoiceGroupObjectPermission = apps.get_model(  # noqa: N806
        "invoices", "InvoiceGroupObjectPermission"
    )
    Permission = apps.get_model("auth", "Permission")  # noqa: N806

    invoices = Invoice.objects.all()

    if invoices.exists():
        view_permission = Permission.objects.get(
            codename="view_invoice",
            content_type__app_label="invoices",
        )

        for invoice in invoices:
            InvoiceGroupObjectPermission.objects.create(
                content_object=invoice,
                group=invoice.challenge.admins_group,
                permission=view_permission,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0005_invoiceuserobjectpermission_and_more"),
    ]

    operations = [
        migrations.RunPython(assign_perms_challenge_admins, elidable=True)
    ]
