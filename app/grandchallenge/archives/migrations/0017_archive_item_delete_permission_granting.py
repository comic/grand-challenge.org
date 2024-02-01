from django.db import migrations
from guardian.shortcuts import assign_perm


def add_archive_item_delete_permissions(apps, schema_editor):
    Archive = apps.get_model("archives", "Archive")  # noqa: N806
    ArchiveItem = apps.get_model("archives", "ArchiveItem")  # noqa: N806

    archives = (
        Archive.objects.order_by("-created")
        .prefetch_related("editors_group", "items")
        .all()
    )
    for batch in archives.iterator(chunk_size=100):
        for archive in batch:
            editors = archive.editors_group.user_set.all()
            for editor in editors:
                assign_perm(
                    f"delete_{ArchiveItem._meta.model_name}",
                    editor,
                    archive.items.all(),
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
