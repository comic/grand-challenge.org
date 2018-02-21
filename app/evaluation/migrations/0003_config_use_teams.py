# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0002_config_daily_submission_limit'),
    ]

    operations = [
        migrations.AddField(
            model_name='config',
            name='use_teams',
            field=models.BooleanField(default=False, help_text='If true, users are able to form teams together to participate in challenges.'),
        ),
    ]
