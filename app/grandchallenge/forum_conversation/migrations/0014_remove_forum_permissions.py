from django.db import migrations


def remove_forum_permissions(apps, schema_editor):
    GroupForumPermission = apps.get_model(  # noqa: N806
        "forum_permission", "GroupForumPermission"
    )
    UserForumPermission = apps.get_model(  # noqa: N806
        "forum_permission", "UserForumPermission"
    )

    GroupForumPermission.objects.all().delete()
    UserForumPermission.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("forum_conversation", "0013_auto_20201220_1745"),
    ]

    operations = [
        migrations.RunPython(remove_forum_permissions, elidable=True),
    ]
