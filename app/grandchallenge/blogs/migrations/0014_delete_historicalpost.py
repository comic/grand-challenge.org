# Generated by Django 4.2.21 on 2025-06-17 12:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "blogs",
            "0013_postgroupobjectpermission_blogs_postg_group_i_4b4b92_idx",
        ),
    ]

    operations = [
        migrations.DeleteModel(
            name="HistoricalPost",
        ),
    ]
