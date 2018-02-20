# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicmodels', '0001_squashed_0016_comicsite_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='comicsite',
            name='use_teams',
            field=models.BooleanField(default=False, help_text='If true, users are able to form teams together to participate in challenges.'),
        ),
    ]
