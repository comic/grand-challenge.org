# Generated by Django 4.2.15 on 2024-08-13 09:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("algorithms", "0052_alter_algorithm_time_limit_alter_job_time_limit"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="is_complimentary",
            field=models.BooleanField(
                default=False,
                editable=False,
                help_text="If True, this job does not consume credits.",
            ),
        ),
    ]
