# Generated by Django 4.2.21 on 2025-05-15 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "uploads",
            "0008_useruploaduserobjectpermission_uploads_use_user_id_866a16_idx",
        ),
    ]

    operations = [
        migrations.AddIndex(
            model_name="useruploadgroupobjectpermission",
            index=models.Index(
                fields=["group", "permission"],
                name="uploads_use_group_i_53998e_idx",
            ),
        ),
    ]
