# Generated by Django 4.2.21 on 2025-05-15 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "teams",
            "0003_teamuserobjectpermission_teams_teamu_user_id_03fef1_idx",
        ),
    ]

    operations = [
        migrations.AddIndex(
            model_name="teamgroupobjectpermission",
            index=models.Index(
                fields=["group", "permission"],
                name="teams_teamg_group_i_88ea09_idx",
            ),
        ),
    ]
