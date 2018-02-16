# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0006_auto_20180213_1406'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ranking',
            name='challenge',
        ),
        migrations.AddField(
            model_name='result',
            name='rank',
            field=models.PositiveIntegerField(default=0, help_text='The position of this result on the leaderboard. If the value is zero, then the result is unranked.'),
        ),
        migrations.DeleteModel(
            name='Ranking',
        ),
    ]
