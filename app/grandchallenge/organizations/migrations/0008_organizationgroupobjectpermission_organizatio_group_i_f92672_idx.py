# Generated by Django 4.2.20 on 2025-05-14 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "organizations",
            "0007_organization_algorithm_maximum_settable_memory_gb_and_more",
        ),
    ]

    operations = [
        migrations.AddIndex(
            model_name="organizationgroupobjectpermission",
            index=models.Index(
                fields=["group", "permission"],
                name="organizatio_group_i_f92672_idx",
            ),
        ),
    ]
