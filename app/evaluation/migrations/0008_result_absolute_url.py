# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation', '0007_auto_20180216_1516'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='absolute_url',
            field=models.TextField(blank=True),
        ),
    ]
