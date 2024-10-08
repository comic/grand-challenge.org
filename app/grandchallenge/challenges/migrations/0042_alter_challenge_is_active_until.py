# Generated by Django 4.2.15 on 2024-09-18 07:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("challenges", "0041_auto_20240918_0740"),
    ]

    operations = [
        migrations.AlterField(
            model_name="challenge",
            name="is_active_until",
            field=models.DateField(
                help_text="The date at which the challenge becomes inactive"
            ),
        ),
    ]
