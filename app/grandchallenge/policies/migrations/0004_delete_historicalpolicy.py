# Generated by Django 4.2.21 on 2025-06-17 12:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("policies", "0003_auto_20220517_0740"),
    ]

    operations = [
        migrations.DeleteModel(
            name="HistoricalPolicy",
        ),
    ]
