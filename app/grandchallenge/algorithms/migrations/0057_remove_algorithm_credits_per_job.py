# Generated by Django 4.2.16 on 2024-10-09 08:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "algorithms",
            "0056_job_credits_consumed_job_requires_gpu_type_and_more",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="algorithm",
            name="credits_per_job",
        ),
    ]