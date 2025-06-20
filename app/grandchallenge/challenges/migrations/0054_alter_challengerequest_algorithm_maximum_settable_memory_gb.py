# Generated by Django 4.2.21 on 2025-06-19 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "challenges",
            "0053_challengeuserobjectpermission_challenges__user_id_7f9623_idx_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="challengerequest",
            name="algorithm_maximum_settable_memory_gb",
            field=models.PositiveSmallIntegerField(
                default=32,
                help_text="Maximum amount of main memory (DRAM) that participants will be allowed to assign to algorithm inference jobs for submission.",
            ),
        ),
    ]
