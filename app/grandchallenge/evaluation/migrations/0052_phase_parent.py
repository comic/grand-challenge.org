# Generated by Django 4.2.11 on 2024-04-24 11:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0051_evaluation_detailed_error_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="phase",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                help_text="Is this phase dependent on another phase? If selected, submissions to the current phase will only be possible after a successful submission has been made to the parent phase. <b>Bear in mind that if you require a successful submission to a sanity check phase in order to submit to a final test phase, it could prevent people from submitting to the test phase on deadline day if the sanity check submission takes a long time to execute. </b>",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="evaluation.phase",
            ),
        ),
    ]