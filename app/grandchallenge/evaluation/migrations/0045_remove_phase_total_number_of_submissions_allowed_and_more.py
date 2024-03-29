# Generated by Django 4.1.11 on 2023-10-04 11:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0044_optionalhangingprotocolphase_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="phase",
            name="total_number_of_submissions_allowed",
        ),
        migrations.AddField(
            model_name="phase",
            name="average_algorithm_job_duration",
            field=models.DurationField(
                null=True,
                editable=False,
                help_text="The average duration of successful algorithm jobs for this phase",
            ),
        ),
        migrations.AddField(
            model_name="phase",
            name="compute_cost_euro_millicents",
            field=models.PositiveBigIntegerField(
                default=0,
                editable=False,
                help_text="The total compute cost for this phase in Euro Cents, including Tax",
            ),
        ),
    ]
