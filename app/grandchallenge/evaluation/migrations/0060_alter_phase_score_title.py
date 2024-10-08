# Generated by Django 4.2.15 on 2024-09-18 11:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "evaluation",
            "0059_alter_evaluation_options_evaluation_claimed_by_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="phase",
            name="score_title",
            field=models.CharField(
                default="Score",
                help_text="The name that will be displayed for the scores column, for instance: Score (log-loss)",
                max_length=64,
            ),
        ),
    ]
