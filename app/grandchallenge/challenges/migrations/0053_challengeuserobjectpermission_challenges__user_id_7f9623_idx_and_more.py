# Generated by Django 4.2.21 on 2025-05-15 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "challenges",
            "0052_challengegroupobjectpermission_challenges__group_i_8a9dd3_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddIndex(
            model_name="challengeuserobjectpermission",
            index=models.Index(
                fields=["user", "permission"],
                name="challenges__user_id_7f9623_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="onboardingtaskuserobjectpermission",
            index=models.Index(
                fields=["user", "permission"],
                name="challenges__user_id_fb69ee_idx",
            ),
        ),
    ]
