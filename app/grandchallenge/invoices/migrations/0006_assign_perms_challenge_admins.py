from django.db import migrations


def assign_perms_challenge_admins(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")  # noqa: N806
    Invoice = apps.get_model("invoices", "Invoice")  # noqa: N806
    InvoiceGroupObjectPermission = apps.get_model(  # noqa: N806
        "invoices", "InvoiceGroupObjectPermission"
    )
    Permission = apps.get_model("auth", "Permission")  # noqa: N806

    queryset = Challenge.objects.order_by("-created").prefetch_related(
        "admins_group", "invoices"
    )
    if queryset.exists():
        view_permission = Permission.objects.get(
            codename=f"view_{Invoice._meta.model_name}",
            content_type__app_label="invoices",
        )

        for challenge in queryset.iterator():
            InvoiceGroupObjectPermission.objects.bulk_create(
                objs=[
                    InvoiceGroupObjectPermission(
                        content_object=invoice,
                        group=challenge.admins_group,
                        permission=view_permission,
                    )
                    for invoice in challenge.invoices.all()
                ],
                ignore_conflicts=True,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0005_invoiceuserobjectpermission_and_more"),
    ]

    operations = [
        migrations.RunPython(assign_perms_challenge_admins, elidable=True)
    ]
