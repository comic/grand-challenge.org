# Generated by Django 4.2.15 on 2024-09-12 09:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("challenges", "0038_alter_challenge_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="challenge",
            name="external_evaluators_group",
            field=models.OneToOneField(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="external_evaluators_of_challenge",
                to="auth.group",
            ),
        ),
    ]
