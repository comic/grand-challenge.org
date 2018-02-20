# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0001_squashed_0008_result_absolute_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='config',
            name='daily_submission_limit',
            field=models.PositiveIntegerField(default=10, help_text='The limit on the number of times that a user can make a submission in a 24 hour period.'),
        ),
    ]
