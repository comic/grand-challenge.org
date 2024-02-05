from django.db import migrations


def add_archive_item_delete_permissions(apps, schema_editor):
    Archive = apps.get_model("archives", "Archive")  # noqa: N806
    ArchiveItem = apps.get_model("archives", "ArchiveItem")  # noqa: N806
    ArchiveItemGroupObjectPermission = apps.get_model(  # noqa: N806
        "archives", "ArchiveItemGroupObjectPermission"
    )
    Permission = apps.get_model("auth", "Permission")  # noqa: N806

    queryset = Archive.objects.order_by("-created").prefetch_related(
        "editors_group", "items"
    )
    if queryset:
        delete_permission = Permission.objects.get(
            codename=f"delete_{ArchiveItem._meta.model_name}",
            content_type__app_label="archives",
        )

        for archive in queryset.iterator():
            ArchiveItemGroupObjectPermission.objects.bulk_create(
                objs=[
                    ArchiveItemGroupObjectPermission(
                        content_object=item,
                        group=archive.editors_group,
                        permission=delete_permission,
                    )
                    for item in archive.items.all()
                ],
                ignore_conflicts=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("archives", "0016_optionalhangingprotocolarchive_and_more"),
    ]

    operations = [
        migrations.RunPython(
            add_archive_item_delete_permissions, elidable=True
        ),
    ]
