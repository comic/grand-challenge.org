from django.db import migrations
from guardian.shortcuts import assign_perm


def add_archive_item_delete_permissions(apps, schema_editor):
    ArchiveItem = apps.get_model("archives", "ArchiveItem")  # noqa: N806

    items = ArchiveItem.objects.order_by("-created").prefetch_related(
        "archive__editors_group"
    )
    for item in items.iterator():
        assign_perm(
            f"delete_{ArchiveItem._meta.model_name}",
            item.archive.editors_group,
            item,
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
