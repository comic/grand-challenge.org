# Generated by Django 4.2.13 on 2024-05-31 14:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("algorithms", "0049_algorithmmodel_job_algorithm_model_and_more"),
        ("evaluation", "0053_alter_phase_extra_results_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="algorithm_model",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="algorithms.algorithmmodel",
            ),
        ),
    ]
