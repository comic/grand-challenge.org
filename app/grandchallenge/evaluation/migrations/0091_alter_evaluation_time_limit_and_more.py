# Generated by Django 4.2.23 on 2025-07-21 13:49

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0090_alter_evaluation_requires_gpu_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="evaluation",
            name="time_limit",
            field=models.PositiveIntegerField(
                help_text="Time limit for the job in seconds",
                validators=[
                    django.core.validators.MinValueValidator(limit_value=300),
                    django.core.validators.MaxValueValidator(
                        limit_value=86400
                    ),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="phase",
            name="algorithm_time_limit",
            field=models.PositiveIntegerField(
                default=1200,
                help_text="Time limit for inference jobs in seconds",
                validators=[
                    django.core.validators.MinValueValidator(limit_value=300),
                    django.core.validators.MaxValueValidator(
                        limit_value=86400
                    ),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="phase",
            name="evaluation_time_limit",
            field=models.PositiveIntegerField(
                default=3600,
                help_text="Time limit for evaluation jobs in seconds",
                validators=[
                    django.core.validators.MinValueValidator(limit_value=300),
                    django.core.validators.MaxValueValidator(
                        limit_value=86400
                    ),
                ],
            ),
        ),
    ]
