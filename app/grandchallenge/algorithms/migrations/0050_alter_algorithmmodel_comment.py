# Generated by Django 4.2.13 on 2024-06-07 08:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("algorithms", "0049_algorithmmodel_job_algorithm_model_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="algorithmmodel",
            name="comment",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Add any information (e.g. version ID) about this object here.",
            ),
        ),
    ]
