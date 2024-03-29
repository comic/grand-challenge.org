# Generated by Django 4.2.9 on 2024-01-09 14:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "reader_studies",
            "0048_alter_answer_answer_alter_historicalanswer_answer_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="readerstudy",
            name="roll_over_answers_for_n_cases",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="The number of cases for which answers should roll over. It can be used for repeated readings with slightly different hangings. For instance, if set to 1. Case 2 will start with the answers from case 1; whereas case 3 starts anew but its answers will roll over to case 4. Setting it to 0 (default) means answers will not roll over.",
            ),
        ),
    ]
