# Generated by Django 3.2.13 on 2022-04-19 11:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reader_studies", "0023_auto_20220414_1527"),
    ]

    operations = [
        migrations.AddField(
            model_name="answer",
            name="last_edit_duration",
            field=models.DurationField(null=True),
        ),
        migrations.AddField(
            model_name="answer",
            name="total_edit_duration",
            field=models.DurationField(null=True),
        ),
        migrations.AddField(
            model_name="historicalanswer",
            name="last_edit_duration",
            field=models.DurationField(null=True),
        ),
        migrations.AddField(
            model_name="historicalanswer",
            name="total_edit_duration",
            field=models.DurationField(null=True),
        ),
    ]