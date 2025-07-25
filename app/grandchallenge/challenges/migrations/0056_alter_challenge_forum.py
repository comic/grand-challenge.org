# Generated by Django 4.2.21 on 2025-07-03 10:40

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("forum", "0011_auto_20190627_2132"),
        ("challenges", "0055_challenge_discussion_forum"),
    ]

    operations = [
        migrations.AlterField(
            model_name="challenge",
            name="forum",
            field=models.OneToOneField(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="forum.forum",
            ),
        ),
    ]
