# Generated by Django 4.2.13 on 2024-06-26 07:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("challenges", "0037_external_evaluators_group"),
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