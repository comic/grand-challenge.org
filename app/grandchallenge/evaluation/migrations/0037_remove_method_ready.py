# Generated by Django 4.1.9 on 2023-06-27 15:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0036_alter_submission_predictions_file"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="method",
            name="ready",
        ),
    ]
